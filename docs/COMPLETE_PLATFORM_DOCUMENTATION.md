# UzTrack Platform: Complete Two-Sided Technical Documentation
### Multi-Carrier Shipping Orchestration & Live Vector Tracking Middleware
*Modeled after Shippo & Narvar Architecture for Uzbekistan Logistics*

---

## 1. Executive Summary & Architecture

UzTrack operates as an **independent shipping orchestration middleware (B2B clearinghouse)**. It sits between **Demand-Side Platforms** (Marketplaces, Classifieds, E-Commerce merchants) and **Supply-Side Delivery Providers** (Fargo Express, EMU, BTS Cargo, UzPost, Yandex Delivery).

```
   DEMAND SIDE                                MIDDLEWARE ENGINE                              SUPPLY SIDE
┌───────────────────────┐                  ┌──────────────────────────────┐              ┌────────────────────────┐
│ OLX.uz (Classifieds)  │                  │                              │              │ Fargo Express (M39)    │
│ Uzum Market (E-Comm)  │◄──── REST API ───┤ UzTrack Orchestration Engine ├─── REST/───►│ EMU Express (Air/Avto) │
│ Asaxiy.uz (Electronics│      & Webhook   │  - Rate Shopping Engine      │    Webhooks  │ BTS Cargo (Hub-to-Hub) │
│ Zoodmall / Merchants  │                  │  - Nearest Domestic Routing  │              │ UzPost (National Post) │
│                       │◄── Drop-In UI ───┤  - Normalized Status FSM     │              │ Yandex Delivery        │
│ [In-App Tracking Map] │    Component     │  - Inspection Photo Vault    │              │                        │
└───────────────────────┘                  └──────────────────────────────┘              └────────────────────────┘
```

### Key Principles
1. **100% White-Label**: Marketplace buyers never see or know about UzTrack. The tracking experience renders seamlessly under the marketplace's own brand identity (`OLX Yetkazish`, `Uzum Ekspress`, `Asaxiy Yetkazib berish`).
2. **Zero Buyer Redirection**: Buyers never get redirected to third-party courier websites. The tracking map and milestones are embedded directly inside the marketplace order page via `<uz-tracking-view>`.
3. **Nearest Domestic Transit Guarantee**: Inter-city routing strictly follows internal Uzbekistan highway corridors (e.g. Tashkent $\rightarrow$ Guliston $\rightarrow$ Yangiyer $\rightarrow$ Dashtobod $\rightarrow$ Zarbdor $\rightarrow$ Jizzax $\rightarrow$ Samarkand), avoiding foreign transit through Kazakhstan's Makhtaaral wedge.

---

## 2. Side 1: Demand Side Integration Guide (For Marketplaces)

### 2.1 Authentication
Every API request from a marketplace must include an API Bearer token in the `Authorization` header:
```http
Authorization: Bearer uz_live_9948201a4e
Content-Type: application/json
```

---

### 2.2 Endpoint: `GET /v1/rates` (Multi-Carrier Rate Shopping & Nearest Route Calculation)
Query all connected carriers in parallel, calculate exact road distance along the nearest domestic highway, and return real-time quotes.

#### Request:
```http
GET /v1/rates?origin=Toshkent&destination=Samarqand&weight_kg=2.0 HTTP/1.1
Host: api.uztrack.uz
Authorization: Bearer uz_live_9948201a4e
```

#### Response:
```json
{
  "origin": "Toshkent",
  "destination": "Samarqand",
  "weight_kg": 2.0,
  "route_calculation": {
    "distance_km": 386.2,
    "transit_hours": 6.5,
    "route_name": "M39 O'zbekiston Janubiy Aylanma Magistrali (Eng yaqin ichki tranzit)",
    "route_corridor": "Toshkent → Yangiyo'l → Chinoz → Sirdaryo → Guliston → Yangiyer → Dashtobod → Zarbdor → Jizzax → Bulung'ur → Samarqand",
    "domestic_only": true,
    "foreign_borders": 0,
    "road_quality": "4 polosali zamonaviy magistral"
  },
  "rates": [
    {
      "carrier_code": "fargo",
      "carrier_name": "Fargo Express",
      "service_name": "Standart Tranzit (M39 Express)",
      "price_uzs": 35000,
      "estimated_days": "1-2 kun",
      "estimated_hours": 6.5,
      "cutoff_time": "18:00",
      "is_recommended": true,
      "badge": "Eng ommabop",
      "features": ["Eshikkacha yetkazish", "SMS xabarnoma", "Sug'urta mavjud", "Masofa: 386.2 km"]
    },
    {
      "carrier_code": "emu",
      "carrier_name": "EMU Express Mail",
      "service_name": "Tezkor Aviatsiya / Avto Ekspress",
      "price_uzs": 45000,
      "estimated_days": "1 kun (Ertasi kuni)",
      "estimated_hours": 4.9,
      "cutoff_time": "19:30",
      "is_recommended": false,
      "badge": "Eng tez",
      "features": ["Ekspress topshirish", "Jonli tracking", "Maxsus qadoq", "Masofa: 386.2 km"]
    },
    {
      "carrier_code": "bts",
      "carrier_name": "BTS Express Cargo",
      "service_name": "Ombordan-Omborga Kargo",
      "price_uzs": 28000,
      "estimated_days": "2-3 kun",
      "estimated_hours": 9.7,
      "cutoff_time": "17:00",
      "is_recommended": false,
      "badge": "Iqtisodiy kargo",
      "features": ["Qulay narx", "Katta o'lchamli yuklar", "Ombor qabul punkti", "Masofa: 386.2 km"]
    },
    {
      "carrier_code": "uzpost",
      "carrier_name": "UzPost (O'zbekiston Pochtasi)",
      "service_name": "Milliy Pochta Xizmati",
      "price_uzs": 22000,
      "estimated_days": "3-4 kun",
      "estimated_hours": 13.0,
      "cutoff_time": "16:00",
      "is_recommended": false,
      "badge": "Eng keng qamrov",
      "features": ["O'zbekiston bo'ylab 900+ bo'limlar", "Hamyonbop yetkazish", "Masofa: 386.2 km"]
    }
  ]
}
```

---

### 2.3 Endpoint: `POST /v1/shipments` (One-Click Booking & Label Creation)
Marketplace calls this single endpoint to book the delivery. The engine automatically calls the selected courier's internal dispatch system, creates the tracking code, and binds the purchased item data.

#### Request:
```json
POST /v1/shipments HTTP/1.1
Host: api.uztrack.uz
Authorization: Bearer uz_live_9948201a4e
Content-Type: application/json

{
  "external_order_no": "OLX-884920",
  "carrier_code": "fargo",
  "marketplace_id": "olx",
  "sender_city": "Toshkent",
  "recipient_city": "Samarqand",
  "recipient_address": "Samarqand shahar, Registon ko'chasi 14",
  "item": {
    "title": "Apple MacBook Pro 14\" (M3 Pro 18/512GB)",
    "price": 21500000,
    "currency": "UZS",
    "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300",
    "payment_status": "To'langan (Click / Payme)",
    "seller": "Alisher V. (Toshkent, Chilonzor 19)",
    "buyer": "Aziz Karimov (Samarqand, Registon)"
  }
}
```

#### Response:
```json
{
  "success": true,
  "tracking_code": "UZ88492011223",
  "external_order_no": "OLX-884920",
  "carrier": {
    "code": "fargo",
    "name": "Fargo Express",
    "support_phone": "+998712000000"
  },
  "tracking_embed_url": "/?code=UZ88492011223&brand=olx&embed=true",
  "shipment": {
    "status": "ORDER_CREATED",
    "created_at": "2026-10-27T10:00:00Z"
  }
}
```

---

### 2.4 Frontend Integration: Drop-in Web Component (`<uz-tracking-view>`)
The marketplace inserts the custom HTML tag inside their order tracking page:

```html
<!-- 1. CDN Script -->
<script src="https://cdn.uztrack.uz/widget.js" async></script>

<!-- 2. Embeddable Element -->
<uz-tracking-view 
  tracking-code="UZ88492011223" 
  brand="olx" 
  theme="light" 
  lang="uz">
</uz-tracking-view>
```

#### Supported Attributes:
| Attribute | Options | Description |
| :--- | :--- | :--- |
| `tracking-code` | e.g. `UZ88492011223` | Universal UZ-LTS tracking number. |
| `brand` | `olx`, `uzum`, `asaxiy`, `zoodmall` | Adapts theme colors, badges, and accents. |
| `theme` | `light`, `dark` | Map tile and UI drawer brightness. |
| `lang` | `uz`, `ru`, `en` | Multi-language localization for labels and checkpoints. |

---

### 2.5 Outbound Marketplace Webhooks
The marketplace configures a webhook URL (e.g., `https://olx.uz/api/shipping/webhook`). The engine pushes signed JSON events on status changes:

```json
POST /api/shipping/webhook HTTP/1.1
Host: olx.uz
X-UzTrack-Signature: sha256=d3b07384d113edec49eaa6238ad5ff00...
Content-Type: application/json

{
  "event": "shipment.status_changed",
  "tracking_code": "UZ88492011223",
  "external_order_no": "OLX-884920",
  "marketplace_id": "olx",
  "carrier_code": "fargo",
  "standardized_status": "IN_TRANSIT",
  "title_uz": "Shaharlararo yo'lda",
  "location": "Jizzax M39 Nazorati",
  "lat": 40.1158,
  "lng": 67.8422,
  "timestamp": "2026-10-27T10:15:00Z"
}
```

---

## 3. Side 2: Supply Side Integration Guide (For Couriers)

### 3.1 Endpoint: `POST /v1/carrier/manifests` (Pickup Dispatch Manifest)
Couriers query or download batch dispatch manifests of all packages assigned to them across all marketplaces:

```http
POST /v1/carrier/manifests HTTP/1.1
Host: api.uztrack.uz
Authorization: Bearer carrier_secret_key_fargo
Content-Type: application/json

{
  "carrier_code": "fargo"
}
```

#### Response:
```json
{
  "carrier_code": "fargo",
  "manifest_id": "MNF-FARGO-1793088328",
  "total_parcels": 2,
  "parcels": [
    {
      "tracking_code": "UZ88492011223",
      "external_order_no": "OLX-884920",
      "sender_city": "Toshkent",
      "recipient_city": "Samarqand",
      "recipient_address": "Registon ko'chasi 14",
      "status": "ORDER_CREATED"
    }
  ]
}
```

---

### 3.2 Endpoint: `POST /v1/carrier/events` (Pushing GPS & Checkpoint Telemetry)
When a courier scans a barcode at a hub or broadcasts vehicle GPS telemetry:

```http
POST /v1/carrier/events HTTP/1.1
Host: api.uztrack.uz
Authorization: Bearer carrier_secret_key_fargo
Content-Type: application/json

{
  "tracking_code": "UZ88492011223",
  "status": "IN_TRANSIT",
  "city": "Jizzax",
  "checkpoint_name": "Jizzax M39 Nazorati",
  "lat": 40.1158,
  "lng": 67.8422,
  "description": "Jo'natma saralashdan o'tdi va Samarqand tomon yo'l oldi."
}
```

---

### 3.3 Status Normalization Matrix (UZ-LTS 8-State Model)

| Engine Canonical Status | Fargo Express | EMU Express | BTS Cargo | UzPost | Consumer Label (UZ) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ORDER_CREATED` | `10_NEW` | `CREATED` | `NEW_DOC` | `REGISTERED` | Buyurtma rasmiylashtirildi |
| `PICKED_UP` | `20_PICKED` | `COURIER_RCV` | `RCV_CLIENT` | `ACCEPTED` | Kuryer qabul qildi |
| `ORIGIN_HUB_IN` | `30_HUB_TASH` | `SORTING_IN` | `WH_IN_TASH` | `SORT_CENTRE` | Bosh omborda (验货 tekshiruv) |
| `IN_TRANSIT` | `40_LINEHAUL` | `IN_FLIGHT` | `EN_ROUTE` | `TRANSIT` | Shaharlararo magistralda |
| `DEST_HUB_IN` | `50_HUB_REG` | `REG_SORT` | `WH_DEST` | `DEST_POST` | Hududiy saralash markazida |
| `OUT_FOR_DELIVERY` | `60_LAST_MILE`| `DELIVERING` | `COURIER_OUT`| `DISPATCHED` | Kuryer yetkazmoqda |
| `DELIVERED` | `70_DELIVERED`| `DELIVERED` | `SUCCESS` | `DELIVERED` | Topshirildi (Xavfsiz bitim yakuni) |
| `EXCEPTION` | `90_EXCEPTION`| `DELAYED` | `PROBLEM` | `HELD` | Tranzit to'xtatildi / Xatolik |

---

### 3.4 Endpoint: `POST /v1/carrier/inspections` (Hub Photo Quality Verification - 验货照)
Inspired by Pinduoduo's physical parcel verification (`验货照`), couriers upload package integrity photos at origin hubs so customers can inspect their goods in transit:

```http
POST /v1/carrier/inspections HTTP/1.1
Host: api.uztrack.uz
Authorization: Bearer carrier_secret_key_fargo
Content-Type: application/json

{
  "tracking_code": "UZ88492011223",
  "photo_url": "https://storage.uztrack.uz/inspections/uz884920_hub_front.jpg",
  "caption_uz": "Apple MacBook Pro 14 ombor qabuli tekshiruvi (验货照)",
  "caption_ru": "Проверка корпуса и комплектации MacBook Pro 14",
  "caption_en": "Physical inspection photo at Fargo sorting hub"
}
```

---

## 4. Verification and Live Sandbox Access

| Component | URL | Description |
| :--- | :--- | :--- |
| **Interactive API Documentation** | `http://localhost:8080/docs.html` | Live Shippo-style developer portal with interactive API console. |
| **Marketplace Live Demo** | `http://localhost:8080/marketplace-demo.html` | Live working prototype for OLX, Uzum, and Asaxiy. |
| **Universal Tracking View** | `http://localhost:8080/?code=UZ88492011223` | Pinduoduo-style 3D vector map with live simulation. |
| **Health Check** | `http://localhost:8080/health` | Service health status. |
