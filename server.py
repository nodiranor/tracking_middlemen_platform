#!/usr/bin/env python3
"""
UzTrack (UZ-LTS) Local Development Server
Mirrors the Go core REST API and serves the interactive 3D cartoon tracking frontend.
"""

import http.server
import json
import os
import re
import socketserver
import time
from urllib.parse import urlparse

PORT = 8080
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")

# In-memory mock database matching internal/storage/memory.go
shipments = {
    "UZ77019283401": {
        "tracking_code": "UZ77019283401",
        "external_order_no": "UZUM-984210",
        "marketplace_id": "uzum",
        "carrier": {
            "code": "fargo",
            "name": "Fargo Express",
            "support_phone": "+998712000000"
        },
        "status": "IN_TRANSIT",
        "eta": "2026-10-26T18:30:00Z",
        "current_location": {
            "city": "Jizzax",
            "hub": "Jizzax M39 tranzit punkti",
            "lat": 40.1158,
            "lng": 67.8422,
            "updated_at": "2026-10-26T15:00:00Z"
        },
        "route": {
            "origin": {"city": "Toshkent", "hub": "Sergeli Hub", "lat": 41.2268, "lng": 69.2198},
            "destination": {"city": "Samarqand", "hub": "Registon Hub", "lat": 39.6542, "lng": 66.9597},
            "waypoints": [
                {"city": "Toshkent", "label": "Sergeli Markaziy Saralash Markazi", "lat": 41.2268, "lng": 69.2198, "is_passed": True},
                {"city": "Yangiyo'l", "label": "M39 Yangiyo'l nazorati", "lat": 41.1167, "lng": 69.0500, "is_passed": True},
                {"city": "Chinoz", "label": "Chinoz daryo o'tish punkti", "lat": 40.9411, "lng": 68.7594, "is_passed": True},
                {"city": "Sirdaryo", "label": "Guliston / Sirdaryo tranziti", "lat": 40.8373, "lng": 68.6618, "is_passed": True},
                {"city": "Jizzax", "label": "Jizzax M39 tranzit nazorati", "lat": 40.1158, "lng": 67.8422, "is_passed": True},
                {"city": "G'allaorol", "label": "G'allaorol dovoni", "lat": 40.0150, "lng": 67.5850, "is_passed": False},
                {"city": "Bulung'ur", "label": "Samarqand kirish punkti", "lat": 39.7611, "lng": 67.2711, "is_passed": False},
                {"city": "Samarqand", "label": "Registon Markaziy Hub", "lat": 39.6542, "lng": 66.9597, "is_passed": False}
            ]
        },
        "courier": {
            "name": "Jasur Aliyev",
            "phone": "+998901234567",
            "avatar_url": "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=150&q=80",
            "vehicle_type": "truck"
        },
        "inspection_photos": [
            {
                "url": "https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=800&q=80",
                "thumb": "https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=300&q=80",
                "caption_uz": "Sergeli saralash omborida jo'natma qadog'i tekshiruvi (验货照)",
                "caption_ru": "Фото фиксации груза на складе Сергели (验货照)",
                "caption_en": "Cargo parcel received at Sergeli sorting hub"
            },
            {
                "url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=800&q=80",
                "thumb": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=300&q=80",
                "caption_uz": "Sifat va butunlik tekshiruvi (Ombor 139 / Fargo)",
                "caption_ru": "Проверка качества и целостности (Склад 139 / Fargo)",
                "caption_en": "Quality and integrity inspection (Hub 139 / Fargo)"
            }
        ],
        "timeline": [
            {
                "code": "IN_TRANSIT",
                "title_uz": "Shaharlararo yo'lda",
                "title_ru": "В пути между городами",
                "title_en": "In Transit",
                "description_uz": "Jo'natma Jizzax orqali Samarqand tomon harakatlanmoqda (M39).",
                "description_ru": "Отправление движется через Джизак в сторону Самарканда (трасса М39).",
                "description_en": "Parcel is in transit passing Jizzakh toward Samarkand (M39).",
                "location_name": "Jizzax M39 tranziti",
                "timestamp": "2026-10-26T15:00:00Z"
            },
            {
                "code": "ORIGIN_HUB_IN",
                "title_uz": "Saralash markazida",
                "title_ru": "В сортировочном центре",
                "title_en": "At Sorting Hub",
                "description_uz": "Toshkent Sergeli saralash markaziga qabul qilindi.",
                "description_ru": "Принято в сортировочном центре Ташкент Сергели.",
                "description_en": "Received at Tashkent Sergeli sorting hub.",
                "location_name": "Toshkent Sergeli Hub",
                "timestamp": "2026-10-26T11:30:00Z"
            },
            {
                "code": "ORDER_CREATED",
                "title_uz": "Buyurtma rasmiylashtirildi",
                "title_ru": "Заказ оформлен",
                "title_en": "Order Created",
                "description_uz": "Marketplaceda jo'natma yorlig'i yaratildi.",
                "description_ru": "Накладная отправления создана в маркетплейсе.",
                "description_en": "Shipment label created on the marketplace.",
                "location_name": "Toshkent",
                "timestamp": "2026-10-26T09:15:00Z"
            }
        ]
    },
    "UZ99800112233": {
        "tracking_code": "UZ99800112233",
        "external_order_no": "OLX-338192",
        "marketplace_id": "olx",
        "carrier": {
            "code": "yandex",
            "name": "Yandex Delivery Uzbekistan",
            "support_phone": "+998712003344"
        },
        "status": "OUT_FOR_DELIVERY",
        "eta": "2026-10-26T17:15:00Z",
        "current_location": {
            "city": "Toshkent",
            "hub": "Chilonzor distribyutsiya punkti",
            "lat": 41.2721,
            "lng": 69.2012,
            "updated_at": "2026-10-26T16:00:00Z"
        },
        "route": {
            "origin": {"city": "Toshkent", "hub": "Chilonzor 19-mavze", "lat": 41.2721, "lng": 69.2012},
            "destination": {"city": "Toshkent", "hub": "Amir Temur shox ko'chasi 45", "lat": 41.3200, "lng": 69.2830},
            "waypoints": [
                {"city": "Toshkent", "label": "Chilonzor Hub", "lat": 41.2721, "lng": 69.2012, "is_passed": True},
                {"city": "Toshkent", "label": "Bunyodkor shoh", "lat": 41.2850, "lng": 69.2250, "is_passed": True},
                {"city": "Toshkent", "label": "O'zbekiston prospekti", "lat": 41.3050, "lng": 69.2600, "is_passed": True},
                {"city": "Toshkent", "label": "Yetkazish manzili", "lat": 41.3200, "lng": 69.2830, "is_passed": False}
            ]
        },
        "courier": {
            "name": "Bobur Temirov",
            "phone": "+998939988776",
            "avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150&q=80",
            "vehicle_type": "scooter"
        },
        "timeline": [
            {
                "code": "OUT_FOR_DELIVERY",
                "title_uz": "Kuryer yetkazmoqda",
                "title_ru": "Курьер доставляет",
                "title_en": "Out for Delivery",
                "description_uz": "Kuryer Bobur Temirov jo'natmani skuterda yetkazmoqda.",
                "description_ru": "Курьер Бобур Темиров везет заказ на скутере.",
                "description_en": "Courier Bobur Temirov is delivering via scooter.",
                "location_name": "Toshkent Chilonzor",
                "timestamp": "2026-10-26T16:00:00Z"
            }
        ]
    }
}

class UzTrackHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        
        # API: GET /v1/tracks/{code}
        match = re.match(r"^/v1/tracks/([A-Za-z0-9_-]+)$", parsed.path)
        if match:
            code = match.group(1)
            if code in shipments:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(shipments[code]).encode('utf-8'))
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": True, "message": "Shipment not found"}).encode('utf-8'))
            return

        # API: GET /v1/carriers
        if parsed.path == "/v1/carriers":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            carriers = [
                {"code": "fargo", "name": "Fargo Express", "phone": "+998712000000"},
                {"code": "bts", "name": "BTS Express Cargo", "phone": "+998712072020"},
                {"code": "emu", "name": "EMU Express Mail", "phone": "+998712009669"},
                {"code": "yandex", "name": "Yandex Delivery", "phone": "+998712003344"}
            ]
            self.wfile.write(json.dumps({"carriers": carriers}).encode('utf-8'))
            return

        # API: GET /health
        if parsed.path == "/health":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "service": "UzTrack Clearinghouse"}).encode('utf-8'))
            return

        # Otherwise serve static frontend
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)

        # API: POST /v1/tracks/{code}/simulate-hour
        match = re.match(r"^/v1/tracks/([A-Za-z0-9_-]+)/simulate-hour$", parsed.path)
        if match:
            code = match.group(1)
            if code in shipments:
                s = shipments[code]
                wps = s["route"]["waypoints"]
                for i in range(len(wps)):
                    if not wps[i]["is_passed"]:
                        wps[i]["is_passed"] = True
                        s["current_location"] = {
                            "city": wps[i]["city"],
                            "hub": wps[i]["label"],
                            "lat": wps[i]["lat"],
                            "lng": wps[i]["lng"],
                            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                        }
                        if i == len(wps) - 1:
                            s["status"] = "DEST_HUB_IN"
                        else:
                            s["status"] = "IN_TRANSIT"

                        s["timeline"].insert(0, {
                            "code": s["status"],
                            "title_uz": f"Soatlik yangilanish: {wps[i]['city']}",
                            "title_ru": f"Почасовое обновление: {wps[i]['city']}",
                            "title_en": f"Hourly update: {wps[i]['city']}",
                            "description_uz": f"Jo'natma {wps[i]['label']} nazorat punktidan muvaffaqiyatli o'tdi.",
                            "description_ru": f"Отправление успешно прошло контрольный пункт {wps[i]['label']}.",
                            "description_en": f"Parcel successfully passed checkpoint {wps[i]['label']}.",
                            "location_name": wps[i]["label"],
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                        })
                        break

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(s).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
            return

        # API: POST /v1/carriers/{code}/webhook
        match = re.match(r"^/v1/carriers/([A-Za-z0-9_-]+)/webhook$", parsed.path)
        if match:
            carrier = match.group(1)
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))

            code = data.get("tracking_code")
            if code in shipments:
                shipments[code]["timeline"].insert(0, {
                    "code": "UPDATED",
                    "title_uz": "Holat yangilandi",
                    "title_ru": "Статус обновлен",
                    "title_en": "Status Updated",
                    "description_uz": data.get("note", "Kuryer tizimidan holat qabul qilindi"),
                    "description_ru": data.get("note", "Статус обновлен курьерской службой"),
                    "description_en": data.get("note", "Status received from carrier"),
                    "location_name": data.get("hub_name", ""),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                })
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "normalized_status": "IN_TRANSIT"}).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True

    print(f"[UzTrack] Dev Server running on http://localhost:{PORT}")
    print(f"[UzTrack] Tracking Demo: http://localhost:{PORT}/?code=UZ77019283401")
    with ThreadingServer(("", PORT), UzTrackHandler) as httpd:
        httpd.serve_forever()
