package storage

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"uztrack/internal/domain"
)

// PostgresRepository implements storage.Repository using PostgreSQL 16 + PostGIS.
type PostgresRepository struct {
	db *sql.DB
}

// NewPostgresRepository initializes a connection to the PostgreSQL PostGIS database.
func NewPostgresRepository(db *sql.DB) *PostgresRepository {
	return &PostgresRepository{db: db}
}

// GetShipmentByTrackingCode retrieves a shipment with its route waypoints and checkpoint timeline.
func (r *PostgresRepository) GetShipmentByTrackingCode(code string) (*domain.Shipment, error) {
	query := `
		SELECT 
			id, tracking_code, external_order_no, marketplace_id, carrier_code, 
			status, recipient_name, recipient_phone,
			origin_city, origin_hub, origin_lat, origin_lng,
			dest_city, dest_hub, dest_lat, dest_lng,
			current_city, current_hub, current_lat, current_lng,
			eta, created_at, updated_at
		FROM shipments
		WHERE tracking_code = $1
		LIMIT 1;
	`

	var s domain.Shipment
	var eta sql.NullTime
	var origLat, origLng, destLat, destLng, curLat, curLng sql.NullFloat64
	var origHub, destHub, curCity, curHub sql.NullString
	var rName, rPhone sql.NullString

	err := r.db.QueryRow(query, code).Scan(
		&s.ID, &s.TrackingCode, &s.ExternalOrderNo, &s.MarketplaceID, &s.CarrierCode,
		&s.Status, &rName, &rPhone,
		&s.Route.Origin.City, &origHub, &origLat, &origLng,
		&s.Route.Destination.City, &destHub, &destLat, &destLng,
		&curCity, &curHub, &curLat, &curLng,
		&eta, &s.CreatedAt, &s.UpdatedAt,
	)

	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, ErrShipmentNotFound
		}
		return nil, fmt.Errorf("failed to query shipment: %w", err)
	}

	if eta.Valid {
		s.ETA = &eta.Time
	}
	if rName.Valid {
		s.RecipientName = rName.String
	}
	if rPhone.Valid {
		s.RecipientPhone = rPhone.String
	}

	s.Route.Origin.Hub = origHub.String
	s.Route.Origin.Lat = origLat.Float64
	s.Route.Origin.Lng = origLng.Float64

	s.Route.Destination.Hub = destHub.String
	s.Route.Destination.Lat = destLat.Float64
	s.Route.Destination.Lng = destLng.Float64

	s.CurrentLocation = domain.Location{
		City:      curCity.String,
		Hub:       curHub.String,
		Lat:       curLat.Float64,
		Lng:       curLng.Float64,
		UpdatedAt: s.UpdatedAt,
	}

	// Fetch Checkpoint Timeline
	checkpoints, err := r.getCheckpointsForShipment(s.ID)
	if err == nil {
		s.Timeline = checkpoints
	}

	return &s, nil
}

// getCheckpointsForShipment retrieves the immutable event milestones for a shipment.
func (r *PostgresRepository) getCheckpointsForShipment(shipmentID string) ([]domain.Checkpoint, error) {
	query := `
		SELECT code, title_uz, title_ru, title_en, description_uz, description_ru, description_en, 
		       location_name, lat, lng, created_at
		FROM checkpoints
		WHERE shipment_id = $1
		ORDER BY created_at DESC;
	`
	rows, err := r.db.Query(query, shipmentID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var checkpoints []domain.Checkpoint
	for rows.Next() {
		var cp domain.Checkpoint
		var lat, lng sql.NullFloat64
		var locName sql.NullString
		var dUz, dRu, dEn sql.NullString

		if err := rows.Scan(
			&cp.Code, &cp.TitleUz, &cp.TitleRu, &cp.TitleEn,
			&dUz, &dRu, &dEn,
			&locName, &lat, &lng, &cp.Timestamp,
		); err != nil {
			continue
		}

		cp.DescriptionUz = dUz.String
		cp.DescriptionRu = dRu.String
		cp.DescriptionEn = dEn.String
		cp.LocationName = locName.String
		cp.Lat = lat.Float64
		cp.Lng = lng.Float64

		checkpoints = append(checkpoints, cp)
	}

	return checkpoints, nil
}

// SaveShipment stores a new shipment in PostgreSQL.
func (r *PostgresRepository) SaveShipment(s *domain.Shipment) error {
	tx, err := r.db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()

	query := `
		INSERT INTO shipments (
			id, tracking_code, external_order_no, marketplace_id, carrier_code,
			status, recipient_name, recipient_phone,
			origin_city, origin_hub, origin_lat, origin_lng,
			dest_city, dest_hub, dest_lat, dest_lng,
			current_city, current_hub, current_lat, current_lng,
			eta, created_at, updated_at
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8,
			$9, $10, $11, $12,
			$13, $14, $15, $16,
			$17, $18, $19, $20,
			$21, $22, $23
		)
		ON CONFLICT (tracking_code) DO UPDATE SET
			status = EXCLUDED.status,
			current_city = EXCLUDED.current_city,
			current_hub = EXCLUDED.current_hub,
			current_lat = EXCLUDED.current_lat,
			current_lng = EXCLUDED.current_lng,
			updated_at = EXCLUDED.updated_at;
	`

	_, err = tx.Exec(query,
		s.ID, s.TrackingCode, s.ExternalOrderNo, s.MarketplaceID, s.CarrierCode,
		s.Status, s.RecipientName, s.RecipientPhone,
		s.Route.Origin.City, s.Route.Origin.Hub, s.Route.Origin.Lat, s.Route.Origin.Lng,
		s.Route.Destination.City, s.Route.Destination.Hub, s.Route.Destination.Lat, s.Route.Destination.Lng,
		s.CurrentLocation.City, s.CurrentLocation.Hub, s.CurrentLocation.Lat, s.CurrentLocation.Lng,
		s.ETA, s.CreatedAt, s.UpdatedAt,
	)
	if err != nil {
		return fmt.Errorf("failed to insert shipment: %w", err)
	}

	// Insert initial checkpoints if any
	for _, cp := range s.Timeline {
		cpQuery := `
			INSERT INTO checkpoints (
				shipment_id, code, title_uz, title_ru, title_en,
				description_uz, description_ru, description_en,
				location_name, lat, lng, created_at
			) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12);
		`
		_, _ = tx.Exec(cpQuery,
			s.ID, cp.Code, cp.TitleUz, cp.TitleRu, cp.TitleEn,
			cp.DescriptionUz, cp.DescriptionRu, cp.DescriptionEn,
			cp.LocationName, cp.Lat, cp.Lng, cp.Timestamp,
		)
	}

	return tx.Commit()
}

// UpdateShipmentStatus validates transition and saves new status and checkpoint.
func (r *PostgresRepository) UpdateShipmentStatus(code string, status domain.ShipmentStatus, loc domain.Location, note string) (*domain.Shipment, error) {
	current, err := r.GetShipmentByTrackingCode(code)
	if err != nil {
		return nil, err
	}

	if !domain.IsValidTransition(current.Status, status) {
		return nil, fmt.Errorf("%w: invalid transition from %s to %s", ErrInvalidStatus, current.Status, status)
	}

	tx, err := r.db.Begin()
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()

	now := time.Now().UTC()
	updateQuery := `
		UPDATE shipments
		SET status = $1, current_city = $2, current_hub = $3, current_lat = $4, current_lng = $5, updated_at = $6
		WHERE tracking_code = $7;
	`
	_, err = tx.Exec(updateQuery, status, loc.City, loc.Hub, loc.Lat, loc.Lng, now, code)
	if err != nil {
		return nil, err
	}

	cp := domain.NewCheckpoint(status, loc.Hub, loc.Lat, loc.Lng)
	if note != "" {
		cp.DescriptionUz = note
		cp.DescriptionRu = note
		cp.DescriptionEn = note
	}

	cpQuery := `
		INSERT INTO checkpoints (
			shipment_id, code, title_uz, title_ru, title_en,
			description_uz, description_ru, description_en,
			location_name, lat, lng, created_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12);
	`
	_, err = tx.Exec(cpQuery,
		current.ID, cp.Code, cp.TitleUz, cp.TitleRu, cp.TitleEn,
		cp.DescriptionUz, cp.DescriptionRu, cp.DescriptionEn,
		cp.LocationName, cp.Lat, cp.Lng, cp.Timestamp,
	)
	if err != nil {
		return nil, err
	}

	if err := tx.Commit(); err != nil {
		return nil, err
	}

	return r.GetShipmentByTrackingCode(code)
}

// ListActiveShipments finds all shipments not in terminal state.
func (r *PostgresRepository) ListActiveShipments() ([]*domain.Shipment, error) {
	query := `
		SELECT tracking_code FROM shipments
		WHERE status NOT IN ('DELIVERED', 'RETURNED')
		ORDER BY updated_at DESC
		LIMIT 500;
	`
	rows, err := r.db.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*domain.Shipment
	for rows.Next() {
		var code string
		if err := rows.Scan(&code); err == nil {
			if s, err := r.GetShipmentByTrackingCode(code); err == nil {
				list = append(list, s)
			}
		}
	}
	return list, nil
}

// GetCarrier retrieves a carrier by code.
func (r *PostgresRepository) GetCarrier(code string) (*domain.Carrier, error) {
	query := `SELECT code, name, support_phone, is_active FROM carriers WHERE code = $1 LIMIT 1;`
	var c domain.Carrier
	err := r.db.QueryRow(query, code).Scan(&c.Code, &c.Name, &c.SupportPhone, &c.IsActive)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, ErrCarrierNotFound
		}
		return nil, err
	}
	return &c, nil
}

// ListCarriers returns all registered carriers in Uzbekistan.
func (r *PostgresRepository) ListCarriers() ([]*domain.Carrier, error) {
	query := `SELECT code, name, support_phone, is_active FROM carriers WHERE is_active = TRUE ORDER BY name ASC;`
	rows, err := r.db.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*domain.Carrier
	for rows.Next() {
		var c domain.Carrier
		if err := rows.Scan(&c.Code, &c.Name, &c.SupportPhone, &c.IsActive); err == nil {
			list = append(list, &c)
		}
	}
	return list, nil
}

// SpatialNearestHub uses PostGIS ST_Distance to find the nearest regional sorting center in Uzbekistan.
func (r *PostgresRepository) SpatialNearestHub(lat, lng float64) (string, string, float64, error) {
	query := `
		SELECT code, name, ST_Distance(geom, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography) AS dist_meters
		FROM hubs
		ORDER BY dist_meters ASC
		LIMIT 1;
	`
	var code, name string
	var dist float64
	err := r.db.QueryRow(query, lng, lat).Scan(&code, &name, &dist)
	if err != nil {
		return "", "", 0, err
	}
	return code, name, dist, nil
}
