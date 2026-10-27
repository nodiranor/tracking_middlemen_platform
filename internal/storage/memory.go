package storage

import (
	"errors"
	"fmt"
	"sync"
	"time"

	"uztrack/internal/domain"
)

var (
	ErrShipmentNotFound = errors.New("shipment not found")
	ErrCarrierNotFound  = errors.New("carrier not found")
	ErrInvalidStatus    = errors.New("invalid status transition")
)

// Repository defines the persistence interface for UzTrack.
type Repository interface {
	GetShipmentByTrackingCode(code string) (*domain.Shipment, error)
	SaveShipment(s *domain.Shipment) error
	UpdateShipmentStatus(code string, status domain.ShipmentStatus, loc domain.Location, note string) (*domain.Shipment, error)
	ListActiveShipments() ([]*domain.Shipment, error)
	GetCarrier(code string) (*domain.Carrier, error)
	ListCarriers() ([]*domain.Carrier, error)
}

// MemoryRepository is a high-speed, thread-safe in-memory cache/datastore.
type MemoryRepository struct {
	mu        sync.RWMutex
	shipments map[string]*domain.Shipment
	carriers  map[string]*domain.Carrier
}

// NewMemoryRepository initializes the repository with default Uzbekistan carriers and demonstration parcels.
func NewMemoryRepository() *MemoryRepository {
	repo := &MemoryRepository{
		shipments: make(map[string]*domain.Shipment),
		carriers:  make(map[string]*domain.Carrier),
	}
	repo.seedCarriers()
	repo.seedDemoShipments()
	return repo
}

func (r *MemoryRepository) seedCarriers() {
	carriers := []*domain.Carrier{
		{
			Code:         "fargo",
			Name:         "Fargo Express",
			SupportPhone: "+998712000000",
			LogoURL:      "https://cdn.track.uz/carriers/fargo.png",
			IsActive:     true,
		},
		{
			Code:         "bts",
			Name:         "BTS Express Cargo",
			SupportPhone: "+998712072020",
			LogoURL:      "https://cdn.track.uz/carriers/bts.png",
			IsActive:     true,
		},
		{
			Code:         "emu",
			Name:         "EMU Express Mail Uzbekistan",
			SupportPhone: "+998712009669",
			LogoURL:      "https://cdn.track.uz/carriers/emu.png",
			IsActive:     true,
		},
		{
			Code:         "yandex",
			Name:         "Yandex Delivery Uzbekistan",
			SupportPhone: "+998712003344",
			LogoURL:      "https://cdn.track.uz/carriers/yandex.png",
			IsActive:     true,
		},
		{
			Code:         "uzpost",
			Name:         "O'zbekiston Pochtasi (UzPost)",
			SupportPhone: "+998712335747",
			LogoURL:      "https://cdn.track.uz/carriers/uzpost.png",
			IsActive:     true,
		},
	}

	for _, c := range carriers {
		r.carriers[c.Code] = c
	}
}

func (r *MemoryRepository) seedDemoShipments() {
	now := time.Now().UTC()
	t1 := now.Add(-6 * time.Hour)
	t2 := now.Add(-3 * time.Hour)
	t3 := now.Add(-1 * time.Hour)
	eta := now.Add(4 * time.Hour)

	// Demo 1: Tashkent -> Samarkand (Currently In Transit via Jizzakh)
	passedTrue := true
	passedFalse := false
	shipment1 := &domain.Shipment{
		ID:              "shp_01",
		TrackingCode:    "UZ77019283401",
		ExternalOrderNo: "UZUM-984210",
		MarketplaceID:   "uzum",
		CarrierCode:     "fargo",
		Status:          domain.StatusInTransit,
		ETA:             &eta,
		RecipientName:   "Alisher Qodirov",
		RecipientPhone:  "+99890***4411",
		CurrentLocation: domain.Location{
			City:      "Jizzax",
			Hub:       "Jizzax M39 tranzit punkti",
			Lat:       40.1158,
			Lng:       67.8422,
			UpdatedAt: t3,
		},
		Route: domain.RouteDefinition{
			Origin: domain.Location{
				City:      "Toshkent",
				Hub:       "Sergeli Markaziy Saralash Markazi",
				Lat:       41.2268,
				Lng:       69.2198,
				UpdatedAt: t1,
			},
			Destination: domain.Location{
				City:      "Samarqand",
				Hub:       "Samarqand Shahar Saralash Markazi",
				Lat:       39.6542,
				Lng:       66.9597,
				UpdatedAt: eta,
			},
			Waypoints: []domain.Waypoint{
				{Index: 0, City: "Toshkent", Label: "Sergeli Hub", Lat: 41.2268, Lng: 69.2198, IsPassed: passedTrue, PassedAt: &t1},
				{Index: 1, City: "Sirdaryo", Label: "Guliston tranziti", Lat: 40.4912, Lng: 68.7842, IsPassed: passedTrue, PassedAt: &t2},
				{Index: 2, City: "Jizzax", Label: "Jizzax tranzit nazorati", Lat: 40.1158, Lng: 67.8422, IsPassed: passedTrue, PassedAt: &t3},
				{Index: 3, City: "Bulung'ur", Label: "Samarqand kirish punkti", Lat: 39.7611, Lng: 67.2711, IsPassed: passedFalse},
				{Index: 4, City: "Samarqand", Label: "Registon Markaziy Hub", Lat: 39.6542, Lng: 66.9597, IsPassed: passedFalse},
			},
		},
		Courier: &domain.CourierInfo{
			Name:        "Jasur Aliyev",
			Phone:       "+998901234567",
			AvatarURL:   "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=150&q=80",
			VehicleType: domain.VehicleTruck,
		},
		Timeline: []domain.Checkpoint{
			{
				Code:          domain.StatusInTransit,
				TitleUz:       "Shaharlararo yo'lda",
				TitleRu:       "В пути между городами",
				TitleEn:       "In Transit",
				DescriptionUz: "Jo'natma Jizzax orqali Samarqand tomon harakatlanmoqda (M39).",
				DescriptionRu: "Отправление движется через Джизак в сторону Самарканда (трасса М39).",
				DescriptionEn: "Parcel is in transit passing Jizzakh toward Samarkand (M39 highway).",
				LocationName:  "Jizzax M39 tranziti",
				Lat:           40.1158,
				Lng:           67.8422,
				Timestamp:     t3,
			},
			{
				Code:          domain.StatusOriginHubIn,
				TitleUz:       "Saralash markazida",
				TitleRu:       "В сортировочном центре",
				TitleEn:       "At Sorting Hub",
				DescriptionUz: "Toshkent Sergeli saralash markaziga qabul qilindi.",
				DescriptionRu: "Принято в сортировочном центре Ташкент Сергели.",
				DescriptionEn: "Received at Tashkent Sergeli sorting hub.",
				LocationName:  "Toshkent Sergeli Hub",
				Lat:           41.2268,
				Lng:           69.2198,
				Timestamp:     t2,
			},
			{
				Code:          domain.StatusOrderCreated,
				TitleUz:       "Buyurtma rasmiylashtirildi",
				TitleRu:       "Заказ оформлен",
				TitleEn:       "Order Created",
				DescriptionUz: "Marketplaceda jo'natma yorlig'i yaratildi va yetkazishga tayyorlandi.",
				DescriptionRu: "Накладная отправления создана в маркетплейсе.",
				DescriptionEn: "Shipment label created on the marketplace.",
				LocationName:  "Toshkent",
				Lat:           41.2995,
				Lng:           69.2401,
				Timestamp:     t1,
			},
		},
		CreatedAt: t1,
		UpdatedAt: t3,
	}

	// Demo 2: Intra-city Tashkent (Out for delivery with scooter)
	curLat := 41.311082
	curLng := 69.279737
	eta2 := now.Add(45 * time.Minute)
	shipment2 := &domain.Shipment{
		ID:              "shp_02",
		TrackingCode:    "UZ99800112233",
		ExternalOrderNo: "OLX-338192",
		MarketplaceID:   "olx",
		CarrierCode:     "yandex",
		Status:          domain.StatusOutForDelivery,
		ETA:             &eta2,
		RecipientName:   "Malika Rahimova",
		RecipientPhone:  "+99897***9900",
		CurrentLocation: domain.Location{
			City:      "Toshkent",
			Hub:       "Chilonzor distribyutsiya punkti",
			Lat:       curLat,
			Lng:       curLng,
			UpdatedAt: now,
		},
		Route: domain.RouteDefinition{
			Origin: domain.Location{
				City:      "Toshkent",
				Hub:       "Chilonzor 19-mavze",
				Lat:       41.2721,
				Lng:       69.2012,
				UpdatedAt: t2,
			},
			Destination: domain.Location{
				City:      "Toshkent",
				Hub:       "Amir Temur shox ko'chasi 45",
				Lat:       41.3200,
				Lng:       69.2830,
				UpdatedAt: eta2,
			},
			Waypoints: []domain.Waypoint{
				{Index: 0, City: "Toshkent", Label: "Chilonzor Hub", Lat: 41.2721, Lng: 69.2012, IsPassed: true},
				{Index: 1, City: "Toshkent", Label: "Bunyodkor shoh", Lat: 41.2850, Lng: 69.2250, IsPassed: true},
				{Index: 2, City: "Toshkent", Label: "O'zbekiston prospekti", Lat: 41.3050, Lng: 69.2600, IsPassed: true},
				{Index: 3, City: "Toshkent", Label: "Yetkazish manzili", Lat: 41.3200, Lng: 69.2830, IsPassed: false},
			},
		},
		Courier: &domain.CourierInfo{
			Name:        "Bobur Temirov",
			Phone:       "+998939988776",
			AvatarURL:   "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150&q=80",
			VehicleType: domain.VehicleScooter,
			CurrentLat:  &curLat,
			CurrentLng:  &curLng,
		},
		Timeline: []domain.Checkpoint{
			{
				Code:          domain.StatusOutForDelivery,
				TitleUz:       "Kuryer yetkazmoqda",
				TitleRu:       "Курьер доставляет",
				TitleEn:       "Out for Delivery",
				DescriptionUz: "Kuryer Bobur Temirov jo'natmani manzilingiz tomon olib ketmoqda.",
				DescriptionRu: "Курьер Бобур Темиров везет ваш заказ по указанному адресу.",
				DescriptionEn: "Courier Bobur Temirov is delivering the parcel to your address.",
				LocationName:  "Toshkent Chilonzor",
				Lat:           curLat,
				Lng:           curLng,
				Timestamp:     now,
			},
			{
				Code:          domain.StatusOriginHubIn,
				TitleUz:       "Distribyutsiya punktida",
				TitleRu:       "В пункте распределения",
				TitleEn:       "At Distribution Hub",
				DescriptionUz: "Chilonzor mahalliy distribyutsiya markaziga yetib keldi.",
				DescriptionRu: "Прибыло в пункт распределения Чиланзар.",
				DescriptionEn: "Arrived at local Chilanzar distribution center.",
				LocationName:  "Chilonzor Hub",
				Lat:           41.2721,
				Lng:           69.2012,
				Timestamp:     t2,
			},
		},
		CreatedAt: t2,
		UpdatedAt: now,
	}

	r.shipments[shipment1.TrackingCode] = shipment1
	r.shipments[shipment2.TrackingCode] = shipment2
}

func (r *MemoryRepository) GetShipmentByTrackingCode(code string) (*domain.Shipment, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	s, ok := r.shipments[code]
	if !ok {
		return nil, ErrShipmentNotFound
	}
	return s, nil
}

func (r *MemoryRepository) SaveShipment(s *domain.Shipment) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	s.UpdatedAt = time.Now().UTC()
	r.shipments[s.TrackingCode] = s
	return nil
}

func (r *MemoryRepository) UpdateShipmentStatus(code string, status domain.ShipmentStatus, loc domain.Location, note string) (*domain.Shipment, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	s, ok := r.shipments[code]
	if !ok {
		return nil, ErrShipmentNotFound
	}

	if !domain.IsValidTransition(s.Status, status) {
		return nil, fmt.Errorf("%w: cannot transition from %s to %s", ErrInvalidStatus, s.Status, status)
	}

	s.Status = status
	s.CurrentLocation = loc
	s.UpdatedAt = time.Now().UTC()

	cp := domain.NewCheckpoint(status, loc.Hub, loc.Lat, loc.Lng)
	if note != "" {
		cp.DescriptionUz = note
		cp.DescriptionRu = note
		cp.DescriptionEn = note
	}

	s.Timeline = append([]domain.Checkpoint{cp}, s.Timeline...)
	return s, nil
}

func (r *MemoryRepository) ListActiveShipments() ([]*domain.Shipment, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	var list []*domain.Shipment
	for _, s := range r.shipments {
		if s.Status != domain.StatusDelivered && s.Status != domain.StatusReturned {
			list = append(list, s)
		}
	}
	return list, nil
}

func (r *MemoryRepository) GetCarrier(code string) (*domain.Carrier, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	c, ok := r.carriers[code]
	if !ok {
		return nil, ErrCarrierNotFound
	}
	return c, nil
}

func (r *MemoryRepository) ListCarriers() ([]*domain.Carrier, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	var list []*domain.Carrier
	for _, c := range r.carriers {
		list = append(list, c)
	}
	return list, nil
}
