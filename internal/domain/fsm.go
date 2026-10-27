package domain

import (
	"fmt"
	"time"
)

// AllowedTransitions maps each valid source status to its allowed next statuses.
var AllowedTransitions = map[ShipmentStatus][]ShipmentStatus{
	StatusOrderCreated: {
		StatusPickedUp,
		StatusException,
		StatusReturned,
	},
	StatusPickedUp: {
		StatusOriginHubIn,
		StatusInTransit,
		StatusException,
		StatusReturned,
	},
	StatusOriginHubIn: {
		StatusInTransit,
		StatusDestHubIn,
		StatusException,
		StatusReturned,
	},
	StatusInTransit: {
		StatusDestHubIn,
		StatusOutForDelivery,
		StatusException,
	},
	StatusDestHubIn: {
		StatusOutForDelivery,
		StatusPvzReady,
		StatusException,
		StatusReturned,
	},
	StatusOutForDelivery: {
		StatusDelivered,
		StatusPvzReady,
		StatusException,
	},
	StatusPvzReady: {
		StatusDelivered,
		StatusReturned,
		StatusException,
	},
	StatusException: {
		StatusInTransit,
		StatusOutForDelivery,
		StatusPvzReady,
		StatusReturned,
	},
	StatusDelivered: {}, // Terminal state
	StatusReturned:  {}, // Terminal state
}

// IsValidTransition checks whether transitioning from current to next is permitted by UZ-LTS.
func IsValidTransition(current, next ShipmentStatus) bool {
	// Allow idempotent transitions (same status update)
	if current == next {
		return true
	}
	allowed, ok := AllowedTransitions[current]
	if !ok {
		return false
	}
	for _, s := range allowed {
		if s == next {
			return true
		}
	}
	return false
}

// DefaultMilestoneText generates standardized trilingual descriptions for checkpoints.
func DefaultMilestoneText(status ShipmentStatus, locationName string) (titleUz, titleRu, titleEn, descUz, descRu, descEn string) {
	switch status {
	case StatusOrderCreated:
		return "Buyurtma rasmiylashtirildi", "Заказ оформлен", "Order Created",
			"Marketplaceda jo'natma yorlig'i yaratildi va yetkazishga tayyorlandi.",
			"Накладная отправления создана в маркетплейсе и ожидает передачи курьеру.",
			"Shipment label has been created on the marketplace and is awaiting courier pickup."

	case StatusPickedUp:
		return "Kuryer jo'natmani qabul qildi", "Курьер забрал посылку", "Picked Up by Courier",
			fmt.Sprintf("Kuryer jo'natmani jo'natuvchidan qabul qildi (%s).", locationName),
			fmt.Sprintf("Курьер принял посылку у отправителя (%s).", locationName),
			fmt.Sprintf("Courier collected the parcel from the sender (%s).", locationName)

	case StatusOriginHubIn:
		return "Saralash markaziga yetib keldi", "Прибыло в сортировочный центр", "Arrived at Sorting Hub",
			fmt.Sprintf("%s saralash markaziga qabul qilindi va yo'nalish bo'yicha taqsimlanmoqda.", locationName),
			fmt.Sprintf("Посылка принята в сортировочном центре %s и распределяется по направлению.", locationName),
			fmt.Sprintf("Parcel arrived at %s sorting hub and is being dispatched for line-haul route.", locationName)

	case StatusInTransit:
		return "Shaharlararo yo'lda", "В пути между городами", "In Transit",
			fmt.Sprintf("Jo'natma manzil shahri tomon yo'lga chiqdi (%s orqali).", locationName),
			fmt.Sprintf("Отправление в пути к городу назначения (через %s).", locationName),
			fmt.Sprintf("Parcel is in transit to destination city (passing %s).", locationName)

	case StatusDestHubIn:
		return "Manzil saralash markazida", "Прибыло в город назначения", "Arrived at Destination Hub",
			fmt.Sprintf("%s manzil saralash markaziga yetib keldi va kuryerga biriktirilmoqda.", locationName),
			fmt.Sprintf("Посылка прибыла в сортировочный центр %s и готовится к выдаче курьеру.", locationName),
			fmt.Sprintf("Arrived at %s destination hub and is being prepared for last-mile delivery.", locationName)

	case StatusOutForDelivery:
		return "Kuryer yetkazmoqda", "Курьер доставляет", "Out for Delivery",
			"Jo'natma kuryerga topshirildi va manzil tomon olib ketilmoqda.",
			"Посылка передана курьеру и доставляется по адресу получателя.",
			"Parcel handed over to courier and is out for final delivery to recipient."

	case StatusPvzReady:
		return "Qabul punktida (PVZ) kutmoqda", "Ожидает в пункте выдачи", "Ready for Pickup",
			fmt.Sprintf("Jo'natma %s qabul punktiga yetkazildi. Olib ketishingiz mumkin.", locationName),
			fmt.Sprintf("Посылка доставлена в пункт выдачи заказов %s. Готова к получению.", locationName),
			fmt.Sprintf("Parcel is ready for pickup at %s point.", locationName)

	case StatusDelivered:
		return "Qabul qiluvchiga topshirildi", "Вручено получателю", "Delivered",
			"Jo'natma muvaffaqiyatli qabul qiluvchiga yetkazib berildi. Xaridingiz uchun rahmat!",
			"Посылка успешно вручена получателю. Спасибо за покупку!",
			"Parcel has been successfully delivered to the recipient. Thank you!"

	case StatusException:
		return "Yetkazishda kutilmagan to'siq", "Задержка доставки", "Delivery Exception",
			"Yetkazish vaqtinchalik kechiktirildi yoki manzil aniqlashtirilmoqda.",
			"Доставка временно задержана или уточняется адрес получателя.",
			"Delivery temporarily delayed or recipient address requires clarification."

	case StatusReturned:
		return "Jo'natuvchiga qaytarildi", "Возвращено отправителю", "Returned to Sender",
			"Jo'natma bekor qilindi va jo'natuvchiga qaytarildi.",
			"Посылка отменена и возвращена отправителю.",
			"Shipment was cancelled and returned to the merchant."

	default:
		return "Holat yangilandi", "Статус обновлен", "Status Updated",
			"Jo'natma holati yangilandi.",
			"Статус отправления обновлен.",
			"Shipment status has been updated."
	}
}

// NewCheckpoint creates a validated, timestamped checkpoint.
func NewCheckpoint(status ShipmentStatus, locationName string, lat, lng float64) Checkpoint {
	tUz, tRu, tEn, dUz, dRu, dEn := DefaultMilestoneText(status, locationName)
	return Checkpoint{
		Code:          status,
		TitleUz:       tUz,
		TitleRu:       tRu,
		TitleEn:       tEn,
		DescriptionUz: dUz,
		DescriptionRu: dRu,
		DescriptionEn: dEn,
		LocationName:  locationName,
		Lat:           lat,
		Lng:           lng,
		Timestamp:     time.Now().UTC(),
	}
}
