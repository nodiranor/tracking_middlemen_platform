# UzTrack (UZ-LTS) - Universal Logistics Tracking Engine for Uzbekistan

**UzTrack** is an ultra-fast, lightweight federation and tracking engine designed to bridge **Marketplaces / Classifieds** (Uzum, OLX.uz, Asaxiy, Zoodmall) and **Delivery Companies** (Fargo, BTS, EMU, Yandex, UzPost, regional couriers) across Uzbekistan.

Our primary goal is **not to host or lock in logistics status data**, but to provide an open, standardized engine and embeddable renderer so:
1. **Marketplaces & Classifieds** can easily implement unified live tracking across *any* delivery company without building custom integrations for each courier.
2. **Delivery Companies** can plug in their existing systems (APIs, 1C:Enterprise exports, or Telegram dispatcher bots) without re-engineering their core infrastructure.

---

## Key Capabilities

- **Universal Federation Engine**: Connects to any courier's API, auto-detects carriers from tracking numbers, and normalizes disparate statuses into the standardized UZ-LTS protocol.
- **Real OpenStreetMap Integration**: Renders real-world transport corridors and highways (such as the M39 corridor across Uzbekistan) with OpenStreetMap data.
- **Clean 2D Vector Icons (No Emojis)**: High-definition 2D SVGs for commercial express trucks, delivery scooters, warehouses, and destination pins.
- **Hourly Snapshot Simulation**: Calculates dead-reckoning route progress and delivers scheduled checkpoint updates.
- **Pluggable Architecture for LXC VPS**: High-concurrency Go backend running with minimal memory footprint (< 40MB RAM).
- **Three-Tier Carrier Ingestion**:
  - *Tier 1*: Direct REST / Webhook integrations.
  - *Tier 2*: Batch CSV / Excel importer for 1C:Enterprise dispatchers.
  - *Tier 3*: Smartphone barcode scanner & GPS updater for drivers via Telegram.

---

## Quick Start (Local Demo)

To run the local demonstration engine and interactive map:

```bash
# Start local engine server
python server.py
```

Then open your browser at:
- **Tracking Demo**: [http://localhost:8080/](http://localhost:8080/)
- **Tracking Federation API**: [http://localhost:8080/v1/tracks/UZ77019283401](http://localhost:8080/v1/tracks/UZ77019283401)
- **Health Check**: [http://localhost:8080/health](http://localhost:8080/health)

---

## Repository Structure

```
tracking_middlemen_platform/
├── cmd/
│   └── server/
│       └── main.go                  # Go application entry point, HTTP server & graceful shutdown
├── internal/
│   ├── engine/
│   │   └── engine.go                # Universal federation engine & carrier auto-detection
│   ├── domain/
│   │   ├── shipment.go              # Core domain models (Shipment, Carrier, Checkpoint, Waypoints)
│   │   └── fsm.go                   # UZ-LTS 8-state deterministic finite state machine
│   ├── api/
│   │   ├── router.go                # HTTP router with CORS & logging middleware
│   │   └── handlers.go              # REST endpoints (Tracks, Shipments, Webhooks, Simulation)
│   ├── scheduler/
│   │   └── poller.go                # Hourly tracking scheduler & route waypoint interpolator
│   ├── adapters/
│   │   └── carrier_adapters.go      # Normalization adapters for Fargo, BTS, EMU, Yandex, and Generic
│   └── storage/
│       ├── memory.go                # High-speed in-memory cache
│       └── postgres.go              # PostgreSQL 16 + PostGIS spatial persistence
├── deploy/
│   ├── Dockerfile                   # Multi-stage Alpine container build (~18MB total)
│   ├── docker-compose.yml           # Complete stack: Caddy + Go app + PostGIS + Redis
│   ├── Caddyfile                    # Reverse proxy with Auto-SSL, Brotli, and open CORS
│   ├── deploy-lxc.sh                # 1-click automated setup script for Debian/Ubuntu LXC VPS
│   ├── systemd/
│   │   └── uztrack.service          # Native bare-metal systemd daemon unit for LXC
│   └── db/
│       └── init.sql                 # PostgreSQL 16 + PostGIS schema with Uzbekistan hubs
├── tools/
│   ├── bulk_importer.py             # Tier 2 CSV/Excel batch status updater
│   ├── telegram_courier_bot.py      # Tier 3 Telegram driver scanner & status dispatcher
│   └── sample_dispatch.csv          # Sample waybill manifest for batch testing
├── public/
│   ├── index.html                   # Universal tracking frontend showcase
│   ├── widget.js                    # Universal <uz-tracking-view> Web Component SDK for marketplaces
│   ├── css/
│   │   └── style.css                # Clean 2D UI styling & animations
│   └── js/
│       └── tracking-map.js          # OpenStreetMap engine & 2D SVG vehicle rendering
└── server.py                        # Local dev server for instant testing
```

---

## Marketplace Integration (Drop-in SDK)

Any marketplace or classifieds platform can embed real-time tracking for any supported delivery service with two lines of HTML:

```html
<script src="https://track.uz/widget.js" async></script>
<uz-tracking-view tracking-code="UZ77019283401" lang="uz"></uz-tracking-view>
```

---

## Deployment on LXC VPS

On your Debian or Ubuntu LXC container:

```bash
cd deploy
chmod +x deploy-lxc.sh
./deploy-lxc.sh
```

Or using Docker Compose:
```bash
cd deploy
docker compose up -d --build
```
