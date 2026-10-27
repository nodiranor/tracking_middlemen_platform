package adapters

import (
	"strings"

	"uztrack/internal/domain"
)

// Normalizer interface for converting third-party logistics statuses into UZ-LTS standards.
type Normalizer interface {
	Normalize(rawStatus string) domain.ShipmentStatus
}

// CarrierAdapterRegistry manages adapters for all registered logistics carriers in Uzbekistan.
type CarrierAdapterRegistry struct {
	adapters map[string]Normalizer
}

func NewCarrierAdapterRegistry() *CarrierAdapterRegistry {
	r := &CarrierAdapterRegistry{
		adapters: make(map[string]Normalizer),
	}
	r.adapters["fargo"] = &FargoAdapter{}
	r.adapters["bts"] = &BtsAdapter{}
	r.adapters["emu"] = &EmuAdapter{}
	r.adapters["yandex"] = &YandexAdapter{}
	r.adapters["uzpost"] = &UzPostAdapter{}
	r.adapters["pochta"] = &UzPostAdapter{}
	r.adapters["generic"] = &GenericAdapter{}
	return r
}

func (r *CarrierAdapterRegistry) Get(carrierCode string) Normalizer {
	if a, ok := r.adapters[strings.ToLower(carrierCode)]; ok {
		return a
	}
	return r.adapters["generic"]
}

// FargoAdapter converts Fargo Express internal statuses.
type FargoAdapter struct{}

func (a *FargoAdapter) Normalize(raw string) domain.ShipmentStatus {
	switch strings.ToLower(strings.TrimSpace(raw)) {
	case "order_placed", "draft", "created":
		return domain.StatusOrderCreated
	case "collected", "picked_up", "courier_received":
		return domain.StatusPickedUp
	case "sorting_center", "hub_in", "tashkent_hub":
		return domain.StatusOriginHubIn
	case "in_transit", "on_route", "intercity_linehaul":
		return domain.StatusInTransit
	case "destination_hub", "regional_warehouse":
		return domain.StatusDestHubIn
	case "delivering", "out_for_delivery", "courier_assigned":
		return domain.StatusOutForDelivery
	case "pvz_ready", "waiting_at_point":
		return domain.StatusPvzReady
	case "delivered", "completed", "handed_over":
		return domain.StatusDelivered
	case "failed", "rescheduled", "address_error":
		return domain.StatusException
	case "returned", "cancelled":
		return domain.StatusReturned
	default:
		return domain.StatusInTransit
	}
}

// BtsAdapter converts BTS Cargo internal Russian/Uzbek statuses.
type BtsAdapter struct{}

func (a *BtsAdapter) Normalize(raw string) domain.ShipmentStatus {
	clean := strings.ToLower(strings.TrimSpace(raw))
	switch {
	case strings.Contains(clean, "принят") && strings.Contains(clean, "склад"):
		return domain.StatusOriginHubIn
	case strings.Contains(clean, "принят"):
		return domain.StatusPickedUp
	case strings.Contains(clean, "в пути") || strings.Contains(clean, "jo'natildi"):
		return domain.StatusInTransit
	case strings.Contains(clean, "прибыл") || strings.Contains(clean, "yetib keldi"):
		return domain.StatusDestHubIn
	case strings.Contains(clean, "курьер") || strings.Contains(clean, "dostavka"):
		return domain.StatusOutForDelivery
	case strings.Contains(clean, "вручен") || strings.Contains(clean, "topshirildi"):
		return domain.StatusDelivered
	case strings.Contains(clean, "возврат") || strings.Contains(clean, "qaytarildi"):
		return domain.StatusReturned
	default:
		return domain.StatusInTransit
	}
}

// EmuAdapter converts EMU Express Mail statuses.
type EmuAdapter struct{}

func (a *EmuAdapter) Normalize(raw string) domain.ShipmentStatus {
	clean := strings.ToLower(strings.TrimSpace(raw))
	switch {
	case strings.Contains(clean, "manifest") || clean == "created":
		return domain.StatusOrderCreated
	case strings.Contains(clean, "pickup") || clean == "received":
		return domain.StatusPickedUp
	case strings.Contains(clean, "sorting"):
		return domain.StatusOriginHubIn
	case strings.Contains(clean, "linehaul") || strings.Contains(clean, "transit"):
		return domain.StatusInTransit
	case strings.Contains(clean, "destination"):
		return domain.StatusDestHubIn
	case strings.Contains(clean, "lastmile") || strings.Contains(clean, "courier"):
		return domain.StatusOutForDelivery
	case strings.Contains(clean, "signed") || clean == "delivered":
		return domain.StatusDelivered
	default:
		return domain.StatusInTransit
	}
}

// YandexAdapter converts Yandex Delivery statuses.
type YandexAdapter struct{}

func (a *YandexAdapter) Normalize(raw string) domain.ShipmentStatus {
	switch strings.ToLower(strings.TrimSpace(raw)) {
	case "estimating", "ready_for_approval", "created":
		return domain.StatusOrderCreated
	case "performer_lookup", "performer_draft", "accepted":
		return domain.StatusOrderCreated
	case "performer_found", "pickup_arrived":
		return domain.StatusPickedUp
	case "driving":
		return domain.StatusOutForDelivery
	case "complete", "delivered":
		return domain.StatusDelivered
	case "cancelled", "failed":
		return domain.StatusException
	default:
		return domain.StatusInTransit
	}
}

// UzPostAdapter converts UzPost (O'zbekiston Pochtasi) Russian/Uzbek tracking statuses.
type UzPostAdapter struct{}

func (a *UzPostAdapter) Normalize(raw string) domain.ShipmentStatus {
	clean := strings.ToLower(strings.TrimSpace(raw))
	switch {
	case strings.Contains(clean, "qabul") || strings.Contains(clean, "поступило") || strings.Contains(clean, "принято"):
		return domain.StatusPickedUp
	case strings.Contains(clean, "saralash") || strings.Contains(clean, "сортировка"):
		return domain.StatusOriginHubIn
	case strings.Contains(clean, "yo'lda") || strings.Contains(clean, "в пути") || strings.Contains(clean, "tranzit"):
		return domain.StatusInTransit
	case strings.Contains(clean, "yetib keldi") || strings.Contains(clean, "прибыло в место вручения"):
		return domain.StatusDestHubIn
	case strings.Contains(clean, "kuryer") || strings.Contains(clean, "передано курьеру"):
		return domain.StatusOutForDelivery
	case strings.Contains(clean, "topshirildi") || strings.Contains(clean, "вручено") || strings.Contains(clean, "vrucheno"):
		return domain.StatusDelivered
	case strings.Contains(clean, "qaytarildi") || strings.Contains(clean, "возврат"):
		return domain.StatusReturned
	default:
		return domain.StatusInTransit
	}
}

// GenericAdapter fallback parser using common keyword heuristics.
type GenericAdapter struct{}

func (a *GenericAdapter) Normalize(raw string) domain.ShipmentStatus {
	s := strings.ToUpper(strings.TrimSpace(raw))
	switch s {
	case "CREATED", "ORDER_CREATED", "NEW":
		return domain.StatusOrderCreated
	case "PICKED_UP", "COLLECTED":
		return domain.StatusPickedUp
	case "HUB_IN", "ORIGIN_HUB_IN", "SORTING":
		return domain.StatusOriginHubIn
	case "IN_TRANSIT", "TRANSIT", "SHIPPED":
		return domain.StatusInTransit
	case "DEST_HUB_IN", "ARRIVED":
		return domain.StatusDestHubIn
	case "OUT_FOR_DELIVERY", "DELIVERING":
		return domain.StatusOutForDelivery
	case "PVZ_READY", "PICKUP_POINT":
		return domain.StatusPvzReady
	case "DELIVERED", "DONE", "FINISHED":
		return domain.StatusDelivered
	case "EXCEPTION", "DELAYED", "FAILED":
		return domain.StatusException
	case "RETURNED", "CANCELLED":
		return domain.StatusReturned
	default:
		return domain.StatusInTransit
	}
}
