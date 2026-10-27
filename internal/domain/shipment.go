package domain

import "time"

// ShipmentStatus defines the normalized UZ-LTS 8-state tracking life cycle.
type ShipmentStatus string

const (
	StatusOrderCreated   ShipmentStatus = "ORDER_CREATED"
	StatusPickedUp       ShipmentStatus = "PICKED_UP"
	StatusOriginHubIn    ShipmentStatus = "ORIGIN_HUB_IN"
	StatusInTransit      ShipmentStatus = "IN_TRANSIT"
	StatusDestHubIn      ShipmentStatus = "DEST_HUB_IN"
	StatusOutForDelivery ShipmentStatus = "OUT_FOR_DELIVERY"
	StatusPvzReady       ShipmentStatus = "PVZ_READY"
	StatusDelivered      ShipmentStatus = "DELIVERED"
	StatusException      ShipmentStatus = "EXCEPTION"
	StatusReturned       ShipmentStatus = "RETURNED"
)

// VehicleType defines the type of vehicle used for 3D cartoon avatar rendering.
type VehicleType string

const (
	VehicleTruck   VehicleType = "truck"   // Line-haul intercity freight
	VehicleScooter VehicleType = "scooter" // Neighborhood last-mile moped
	VehicleVan     VehicleType = "van"     // Urban express van
)

// Carrier represents an integrated courier/logistics provider in Uzbekistan.
type Carrier struct {
	Code         string `json:"code"`                   // e.g. "fargo", "bts", "emu", "yandex"
	Name         string `json:"name"`                   // e.g. "Fargo Express"
	SupportPhone string `json:"support_phone"`          // e.g. "+998712000000"
	LogoURL      string `json:"logo_url,omitempty"`     // CDN link
	WebhookURL   string `json:"webhook_url,omitempty"`  // Carrier callback endpoint
	IsActive     bool   `json:"is_active"`
}

// Location represents a geographic point with label and timestamp.
type Location struct {
	City      string    `json:"city"`
	Hub       string    `json:"hub,omitempty"`
	Lat       float64   `json:"lat"`
	Lng       float64   `json:"lng"`
	UpdatedAt time.Time `json:"updated_at"`
}

// Waypoint represents a node along an intercity or intra-city delivery path.
type Waypoint struct {
	Index         int       `json:"index"`
	City          string    `json:"city"`
	Label         string    `json:"label"`
	Lat           float64   `json:"lat"`
	Lng           float64   `json:"lng"`
	IsPassed      bool      `json:"is_passed"`
	PassedAt      *time.Time `json:"passed_at,omitempty"`
	EstimatedTime *time.Time `json:"estimated_time,omitempty"`
}

// CourierInfo details the last-mile delivery agent for customer transparency.
type CourierInfo struct {
	Name        string      `json:"name"`
	Phone       string      `json:"phone"`
	AvatarURL   string      `json:"avatar_url,omitempty"`
	VehicleType VehicleType `json:"vehicle_type"`
	CurrentLat  *float64    `json:"current_lat,omitempty"`
	CurrentLng  *float64    `json:"current_lng,omitempty"`
}

// Checkpoint represents an immutable milestone in the parcel history.
type Checkpoint struct {
	Code          ShipmentStatus `json:"code"`
	TitleUz       string         `json:"title_uz"`
	TitleRu       string         `json:"title_ru"`
	TitleEn       string         `json:"title_en"`
	DescriptionUz string         `json:"description_uz"`
	DescriptionRu string         `json:"description_ru"`
	DescriptionEn string         `json:"description_en"`
	LocationName  string         `json:"location_name"`
	Lat           float64        `json:"lat,omitempty"`
	Lng           float64        `json:"lng,omitempty"`
	Timestamp     time.Time      `json:"timestamp"`
}

// RouteDefinition holds origin, destination, and the polyline/waypoints.
type RouteDefinition struct {
	Origin      Location   `json:"origin"`
	Destination Location   `json:"destination"`
	Waypoints   []Waypoint `json:"waypoints"`
}

// Shipment is the core aggregate root for tracking.
type Shipment struct {
	ID              string          `json:"id"`
	TrackingCode    string          `json:"tracking_code"`    // Universal UZ-LTS tracking number, e.g., "UZ77019283401"
	ExternalOrderNo string          `json:"external_order_no"`// Marketplace internal order ID
	MarketplaceID   string          `json:"marketplace_id"`   // Client identifier (e.g., "uzum", "olx")
	CarrierCode     string          `json:"carrier_code"`     // e.g., "fargo", "bts"
	Status          ShipmentStatus  `json:"status"`
	ETA             *time.Time      `json:"eta,omitempty"`
	CurrentLocation Location        `json:"current_location"`
	Route           RouteDefinition `json:"route"`
	Courier         *CourierInfo    `json:"courier,omitempty"`
	Timeline        []Checkpoint    `json:"timeline"`
	RecipientName   string          `json:"recipient_name,omitempty"`
	RecipientPhone  string          `json:"recipient_phone,omitempty"` // Masked in public APIs
	CreatedAt       time.Time       `json:"created_at"`
	UpdatedAt       time.Time       `json:"updated_at"`
}
