package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"uztrack/internal/adapters"
	"uztrack/internal/domain"
	"uztrack/internal/scheduler"
	"uztrack/internal/storage"
)

// APIHandler wraps dependencies for HTTP endpoints.
type APIHandler struct {
	repo       storage.Repository
	normalizer *adapters.CarrierAdapterRegistry
	poller     *scheduler.Poller
}

func NewAPIHandler(repo storage.Repository, normalizer *adapters.CarrierAdapterRegistry, poller *scheduler.Poller) *APIHandler {
	return &APIHandler{
		repo:       repo,
		normalizer: normalizer,
		poller:     poller,
	}
}

// JSONResponse writes a standardized JSON response.
func JSONResponse(w http.ResponseWriter, statusCode int, data interface{}) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(statusCode)
	_ = json.NewEncoder(w).Encode(data)
}

// ErrorResponse writes an error object.
func ErrorResponse(w http.ResponseWriter, statusCode int, message string) {
	JSONResponse(w, statusCode, map[string]interface{}{
		"error":   true,
		"message": message,
	})
}

// HandleGetTracking returns normalized tracking information for a tracking code.
// GET /v1/tracks/{code}
func (h *APIHandler) HandleGetTracking(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(r.URL.Path, "/")
	if len(parts) < 4 || parts[3] == "" {
		ErrorResponse(w, http.StatusBadRequest, "Tracking code is required in path: /v1/tracks/{code}")
		return
	}
	code := strings.TrimSpace(parts[3])

	shipment, err := h.repo.GetShipmentByTrackingCode(code)
	if err != nil {
		ErrorResponse(w, http.StatusNotFound, fmt.Sprintf("Shipment not found for code: %s", code))
		return
	}

	carrier, _ := h.repo.GetCarrier(shipment.CarrierCode)

	response := map[string]interface{}{
		"tracking_code":     shipment.TrackingCode,
		"external_order_no": shipment.ExternalOrderNo,
		"marketplace_id":   shipment.MarketplaceID,
		"carrier":           carrier,
		"status":            shipment.Status,
		"eta":               shipment.ETA,
		"current_location":  shipment.CurrentLocation,
		"route":             shipment.Route,
		"courier":           shipment.Courier,
		"timeline":          shipment.Timeline,
		"recipient_name":    shipment.RecipientName,
		"recipient_phone":   shipment.RecipientPhone,
		"updated_at":        shipment.UpdatedAt,
	}

	JSONResponse(w, http.StatusOK, response)
}

// CreateShipmentRequest is the payload from marketplaces.
type CreateShipmentRequest struct {
	ExternalOrderNo string   `json:"external_order_no"`
	MarketplaceID   string   `json:"marketplace_id"`
	CarrierCode     string   `json:"carrier_code"`
	SenderCity      string   `json:"sender_city"`
	SenderLat       float64  `json:"sender_lat"`
	SenderLng       float64  `json:"sender_lng"`
	RecipientCity   string   `json:"recipient_city"`
	RecipientLat    float64  `json:"recipient_lat"`
	RecipientLng    float64  `json:"recipient_lng"`
	RecipientName   string   `json:"recipient_name"`
	RecipientPhone  string   `json:"recipient_phone"`
}

// HandleCreateShipment registers a new shipment from a marketplace.
// POST /v1/shipments
func (h *APIHandler) HandleCreateShipment(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		ErrorResponse(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	var req CreateShipmentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		ErrorResponse(w, http.StatusBadRequest, "Invalid JSON payload")
		return
	}

	if req.ExternalOrderNo == "" || req.CarrierCode == "" {
		ErrorResponse(w, http.StatusBadRequest, "external_order_no and carrier_code are required")
		return
	}

	now := time.Now().UTC()
	trackingCode := fmt.Sprintf("UZ%09d", now.UnixNano()%1000000000)

	originLoc := domain.Location{
		City:      req.SenderCity,
		Hub:       req.SenderCity + " Saralash Markazi",
		Lat:       req.SenderLat,
		Lng:       req.SenderLng,
		UpdatedAt: now,
	}
	destLoc := domain.Location{
		City:      req.RecipientCity,
		Hub:       req.RecipientCity + " Yetkazish Markazi",
		Lat:       req.RecipientLat,
		Lng:       req.RecipientLng,
		UpdatedAt: now,
	}

	shipment := &domain.Shipment{
		ID:              fmt.Sprintf("shp_%d", now.Unix()),
		TrackingCode:    trackingCode,
		ExternalOrderNo: req.ExternalOrderNo,
		MarketplaceID:   req.MarketplaceID,
		CarrierCode:     req.CarrierCode,
		Status:          domain.StatusOrderCreated,
		CurrentLocation: originLoc,
		RecipientName:   req.RecipientName,
		RecipientPhone:  req.RecipientPhone,
		Route: domain.RouteDefinition{
			Origin:      originLoc,
			Destination: destLoc,
			Waypoints: []domain.Waypoint{
				{Index: 0, City: req.SenderCity, Label: "Jo'natuvchi punkti", Lat: req.SenderLat, Lng: req.SenderLng, IsPassed: true},
				{Index: 1, City: req.RecipientCity, Label: "Yetkazish manzili", Lat: req.RecipientLat, Lng: req.RecipientLng, IsPassed: false},
			},
		},
		Timeline: []domain.Checkpoint{
			domain.NewCheckpoint(domain.StatusOrderCreated, req.SenderCity, req.SenderLat, req.SenderLng),
		},
		CreatedAt: now,
		UpdatedAt: now,
	}

	if err := h.repo.SaveShipment(shipment); err != nil {
		ErrorResponse(w, http.StatusInternalServerError, "Failed to save shipment")
		return
	}

	JSONResponse(w, http.StatusCreated, shipment)
}

// CarrierWebhookPayload represents incoming raw status updates from courier systems.
type CarrierWebhookPayload struct {
	TrackingCode string  `json:"tracking_code"`
	RawStatus    string  `json:"raw_status"`
	HubName      string  `json:"hub_name"`
	City         string  `json:"city"`
	Lat          float64 `json:"lat"`
	Lng          float64 `json:"lng"`
	Note         string  `json:"note"`
}

// HandleCarrierWebhook ingests raw status from logistics companies and normalizes it.
// POST /v1/carriers/{code}/webhook
func (h *APIHandler) HandleCarrierWebhook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		ErrorResponse(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	parts := strings.Split(r.URL.Path, "/")
	if len(parts) < 5 {
		ErrorResponse(w, http.StatusBadRequest, "Invalid webhook URL format: /v1/carriers/{code}/webhook")
		return
	}
	carrierCode := parts[3]

	var payload CarrierWebhookPayload
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		ErrorResponse(w, http.StatusBadRequest, "Invalid JSON payload")
		return
	}

	normalizer := h.normalizer.Get(carrierCode)
	canonicalStatus := normalizer.Normalize(payload.RawStatus)

	loc := domain.Location{
		City:      payload.City,
		Hub:       payload.HubName,
		Lat:       payload.Lat,
		Lng:       payload.Lng,
		UpdatedAt: time.Now().UTC(),
	}

	updated, err := h.repo.UpdateShipmentStatus(payload.TrackingCode, canonicalStatus, loc, payload.Note)
	if err != nil {
		ErrorResponse(w, http.StatusBadRequest, fmt.Sprintf("Failed to update status: %v", err))
		return
	}

	JSONResponse(w, http.StatusOK, map[string]interface{}{
		"success":          true,
		"normalized_status": canonicalStatus,
		"tracking_code":    updated.TrackingCode,
	})
}

// HandleSimulateHour allows real-time interactive demo advancing 1-hour waypoint progress.
// POST /v1/tracks/{code}/simulate-hour
func (h *APIHandler) HandleSimulateHour(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(r.URL.Path, "/")
	if len(parts) < 5 {
		ErrorResponse(w, http.StatusBadRequest, "Invalid path: /v1/tracks/{code}/simulate-hour")
		return
	}
	code := parts[3]

	updated, err := h.poller.SimulateOneHourStep(code)
	if err != nil {
		ErrorResponse(w, http.StatusBadRequest, fmt.Sprintf("Simulation failed: %v", err))
		return
	}

	JSONResponse(w, http.StatusOK, updated)
}

// HandleListCarriers returns all registered logistics providers in Uzbekistan.
// GET /v1/carriers
func (h *APIHandler) HandleListCarriers(w http.ResponseWriter, r *http.Request) {
	carriers, err := h.repo.ListCarriers()
	if err != nil {
		ErrorResponse(w, http.StatusInternalServerError, "Failed to list carriers")
		return
	}
	JSONResponse(w, http.StatusOK, map[string]interface{}{
		"carriers": carriers,
	})
}
