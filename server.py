#!/usr/bin/env python3
"""
UzTrack (UZ-LTS) Local Development Server
Mirrors the Go core REST API and serves the interactive 3D cartoon tracking frontend.
"""

import http.server
import json
import mimetypes
import os
import re
import socketserver
import time
from urllib.parse import urlparse

mimetypes.add_type('application/json', '.geojson')
mimetypes.add_type('application/json', '.json')

PORT = 8080
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")

# In-memory mock database matching internal/storage/memory.go
shipments = {
    "UZ88492011223": {
        "tracking_code": "UZ88492011223",
        "external_order_no": "OLX-884920",
        "marketplace_id": "olx",
        "carrier": {
            "code": "fargo",
            "name": "Fargo Express",
            "support_phone": "+998712000000"
        },
        "item": {
            "title": "Apple MacBook Pro 14\" (M3 Pro 18/512GB)",
            "price": 21500000,
            "currency": "UZS",
            "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=240&q=80",
            "payment_status": "To'langan (Click / Payme)",
            "seller": "Alisher V. (Toshkent, Chilonzor 19)",
            "buyer": "Aziz Karimov (Samarqand, Registon)"
        },
        "status": "IN_TRANSIT",
        "eta": "2026-10-27T18:30:00Z",
        "current_location": {
            "city": "Jizzax",
            "hub": "Jizzax M39 tranzit punkti",
            "lat": 40.1158,
            "lng": 67.8422,
            "updated_at": "2026-10-27T10:00:00Z"
        },
        "route": {
            "origin": {"city": "Toshkent", "hub": "Toshkent Chilonzor 19", "lat": 41.2268, "lng": 69.2198},
            "destination": {"city": "Samarqand", "hub": "Registon Hub, 14", "lat": 39.6542, "lng": 66.9597},
            "waypoints": [
                {"city": "Toshkent", "label": "Chilonzor qabul punkti", "lat": 41.2268, "lng": 69.2198, "is_passed": True},
                {"city": "Yangiyo'l", "label": "M39 Yangiyo'l nazorati", "lat": 41.1167, "lng": 69.0500, "is_passed": True},
                {"city": "Chinoz", "label": "Chinoz daryo o'tish punkti", "lat": 40.9411, "lng": 68.7594, "is_passed": True},
                {"city": "Sirdaryo", "label": "Sirdaryo tranzit chorrahasi", "lat": 40.8373, "lng": 68.6618, "is_passed": True},
                {"city": "Guliston", "label": "Guliston aylanma tranzit yo'li", "lat": 40.4897, "lng": 68.7847, "is_passed": True},
                {"city": "Yangiyer", "label": "Yangiyer janubiy logistika nuqtasi", "lat": 40.2667, "lng": 68.8167, "is_passed": True},
                {"city": "Dashtobod", "label": "Dashtobod magistral chorrahasi", "lat": 40.1000, "lng": 68.4500, "is_passed": True},
                {"city": "Zarbdor", "label": "Zarbdor orqali Jizzax koridori", "lat": 40.0800, "lng": 68.1700, "is_passed": True},
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
                "url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=800&q=80",
                "thumb": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=300&q=80",
                "caption_uz": "Apple MacBook Pro 14\" tovar holati va qadoq tekshiruvi (验货照)",
                "caption_ru": "Проверка корпуса и комплектации MacBook Pro 14\" (验货照)",
                "caption_en": "Apple MacBook Pro 14 physical inspection photo at hub"
            },
            {
                "url": "https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=800&q=80",
                "thumb": "https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=300&q=80",
                "caption_uz": "Havo-pufakchali himoya qadog'i va plomba (Fargo Hub)",
                "caption_ru": "Защитная упаковка и пломбировка (Fargo Hub)",
                "caption_en": "Protective bubble wrapping and security seal"
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
                "timestamp": "2026-10-27T08:00:00Z"
            },
            {
                "code": "ORIGIN_HUB_IN",
                "title_uz": "Saralash markazida",
                "title_ru": "В сортировочном центре",
                "title_en": "At Sorting Hub",
                "description_uz": "Toshkent Chilonzor saralash markaziga qabul qilindi va tekshirildi.",
                "description_ru": "Принято и проверено в сортировочном центре Ташкент Чиланзар.",
                "description_en": "Received and inspected at Tashkent Chilonzor sorting hub.",
                "location_name": "Toshkent Chilonzor Hub",
                "timestamp": "2026-10-27T06:30:00Z"
            },
            {
                "code": "ORDER_CREATED",
                "title_uz": "Buyurtma rasmiylashtirildi",
                "title_ru": "Заказ оформлен",
                "title_en": "Order Created",
                "description_uz": "OLX orqali xarid qilindi (21,500,000 UZS to'langan). Jo'natma yorlig'i yaratildi.",
                "description_ru": "Куплено через OLX (оплачено 21,500,000 UZS). Накладная создана.",
                "description_en": "Purchased on OLX (21,500,000 UZS paid). Shipment label generated.",
                "location_name": "Toshkent",
                "timestamp": "2026-10-27T05:15:00Z"
            }
        ]
    },
    "UZ77019283401": {
        "tracking_code": "UZ77019283401",
        "external_order_no": "UZUM-984210",
        "marketplace_id": "uzum",
        "carrier": {
            "code": "fargo",
            "name": "Fargo Express",
            "support_phone": "+998712000000"
        },
        "item": {
            "title": "Nike Air Max 270 Sport Sneakers",
            "price": 1450000,
            "currency": "UZS",
            "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=240&q=80",
            "payment_status": "To'langan (Uzum Pay)",
            "seller": "Nike Official Store Tashkent",
            "buyer": "Sardor Rahimov (Samarqand, Registon Hub)"
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
                {"city": "Sirdaryo", "label": "Sirdaryo tranzit chorrahasi", "lat": 40.8373, "lng": 68.6618, "is_passed": True},
                {"city": "Guliston", "label": "Guliston aylanma tranzit yo'li", "lat": 40.4897, "lng": 68.7847, "is_passed": True},
                {"city": "Yangiyer", "label": "Yangiyer janubiy logistika nuqtasi", "lat": 40.2667, "lng": 68.8167, "is_passed": True},
                {"city": "Dashtobod", "label": "Dashtobod magistral chorrahasi", "lat": 40.1000, "lng": 68.4500, "is_passed": True},
                {"city": "Zarbdor", "label": "Zarbdor orqali Jizzax koridori", "lat": 40.0800, "lng": 68.1700, "is_passed": True},
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
        "item": {
            "title": "Sony PlayStation 5 Slim 1TB + DualSense",
            "price": 6800000,
            "currency": "UZS",
            "image_url": "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?auto=format&fit=crop&w=240&q=80",
            "payment_status": "To'langan (Payme)"
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
    },
    "UZ55409182001": {
        "tracking_code": "UZ55409182001",
        "external_order_no": "ASAXIY-409182",
        "marketplace_id": "asaxiy",
        "carrier": {
            "code": "emu",
            "name": "EMU Express Mail",
            "support_phone": "+998712009669"
        },
        "item": {
            "title": "Samsung Galaxy S24 Ultra 12/512GB Titanium",
            "price": 14800000,
            "currency": "UZS",
            "image_url": "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?auto=format&fit=crop&w=240&q=80",
            "payment_status": "To'langan (Asaxiy Nasiya)",
            "seller": "Asaxiy Official Tech Store",
            "buyer": "Jamshid Olimov (Buxoro markaz)"
        },
        "status": "IN_TRANSIT",
        "eta": "2026-10-27T19:00:00Z",
        "current_location": {
            "city": "Jizzax",
            "hub": "EMU Express Markaziy Tranzit Punkti",
            "lat": 40.1158,
            "lng": 67.8422,
            "updated_at": "2026-10-27T10:15:00Z"
        },
        "route": {
            "origin": {"city": "Toshkent", "hub": "Asaxiy Sergeli Ombori", "lat": 41.2268, "lng": 69.2198},
            "destination": {"city": "Buxoro", "hub": "Buxoro EMU Markazi", "lat": 39.7747, "lng": 64.4286},
            "waypoints": [
                {"city": "Toshkent", "label": "Asaxiy Logistika Markazi", "lat": 41.2268, "lng": 69.2198, "is_passed": True},
                {"city": "Jizzax", "label": "Jizzax EMU Tranzit", "lat": 40.1158, "lng": 67.8422, "is_passed": True},
                {"city": "Samarqand", "label": "Samarqand Aylanma Tranzit", "lat": 39.6542, "lng": 66.9597, "is_passed": False},
                {"city": "Buxoro", "label": "Buxoro EMU Markazi", "lat": 39.7747, "lng": 64.4286, "is_passed": False}
            ]
        },
        "courier": {
            "name": "Dilshod Karimov",
            "phone": "+998912348899",
            "avatar_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=150&q=80",
            "vehicle_type": "truck"
        },
        "inspection_photos": [
            {
                "url": "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?auto=format&fit=crop&w=800&q=80",
                "thumb": "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?auto=format&fit=crop&w=300&q=80",
                "caption_uz": "Samsung Galaxy S24 Ultra qadoq va IMEI tekshiruvi (验货照)",
                "caption_ru": "Проверка упаковки и IMEI Samsung Galaxy S24 Ultra (验货照)",
                "caption_en": "Inspection of phone packaging and IMEI integrity"
            }
        ],
        "timeline": [
            {
                "code": "IN_TRANSIT",
                "title_uz": "Shaharlararo yo'lda",
                "title_ru": "В пути между городами",
                "title_en": "In Transit",
                "description_uz": "Jo'natma EMU tezyurar yuk mashinasida Buxoro tomon yo'lda.",
                "description_ru": "Отправление в пути на экспресс-рейсе EMU.",
                "description_en": "Parcel in transit on EMU express route.",
                "location_name": "Jizzax EMU Tranzit",
                "timestamp": "2026-10-27T09:00:00Z"
            }
        ]
    },
    "UZ66772109001": {
        "tracking_code": "UZ66772109001",
        "external_order_no": "ZOOD-772109",
        "marketplace_id": "zoodmall",
        "carrier": {
            "code": "bts",
            "name": "BTS Express Cargo",
            "support_phone": "+998712072020"
        },
        "item": {
            "title": "Sony WH-1000XM5 Wireless Headphones",
            "price": 4200000,
            "currency": "UZS",
            "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=240&q=80",
            "payment_status": "To'langan (ZoodPay)",
            "seller": "Global Cross-Border Hub",
            "buyer": "Malika Yusupova (Toshkent, Mirobod)"
        },
        "status": "IN_TRANSIT",
        "eta": "2026-10-28T14:00:00Z",
        "current_location": {
            "city": "Toshkent",
            "hub": "BTS Shimoliy Kargo Ombori",
            "lat": 41.3500,
            "lng": 69.2900,
            "updated_at": "2026-10-27T10:10:00Z"
        },
        "route": {
            "origin": {"city": "Toshkent", "hub": "BTS Aeroport Kargo terminali", "lat": 41.2570, "lng": 69.2810},
            "destination": {"city": "Toshkent", "hub": "Mirobod filiali", "lat": 41.2900, "lng": 69.2700},
            "waypoints": [
                {"city": "Toshkent", "label": "Bojxona kargo terminali", "lat": 41.2570, "lng": 69.2810, "is_passed": True},
                {"city": "Toshkent", "label": "BTS Shimoliy Kargo Ombori", "lat": 41.3500, "lng": 69.2900, "is_passed": True},
                {"city": "Toshkent", "label": "Mirobod filiali", "lat": 41.2900, "lng": 69.2700, "is_passed": False}
            ]
        },
        "courier": {
            "name": "Rustam Azizov",
            "phone": "+998947761122",
            "avatar_url": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=150&q=80",
            "vehicle_type": "van"
        },
        "inspection_photos": [
            {
                "url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=80",
                "thumb": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=300&q=80",
                "caption_uz": "Sony WH-1000XM5 tovar qadog'i tekshiruvi (验货照)",
                "caption_ru": "Проверка наушников Sony WH-1000XM5 на складе (验货照)",
                "caption_en": "Sony WH-1000XM5 headphones inspection"
            }
        ],
        "timeline": [
            {
                "code": "IN_TRANSIT",
                "title_uz": "Saralashda",
                "title_ru": "На сортировке",
                "title_en": "Sorting",
                "description_uz": "Xalqaro kargo BTS Shimoliy omborida saralanmoqda.",
                "description_ru": "Международный груз проходит сортировку.",
                "description_en": "Cargo is being sorted at BTS hub.",
                "location_name": "BTS Shimoliy Ombor",
                "timestamp": "2026-10-27T07:45:00Z"
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

        # API: GET /v1/rates (Multi-carrier price & ETA comparison)
        if parsed.path == "/v1/rates":
            import urllib.parse
            query = urllib.parse.parse_qs(parsed.query)
            origin = query.get("origin", ["Toshkent"])[0]
            dest = query.get("destination", ["Samarqand"])[0]
            weight = float(query.get("weight_kg", [2.0])[0])

            orig_clean = origin.strip().lower()
            dest_clean = dest.strip().lower()
            is_intra_city = ("toshkent" in orig_clean and "toshkent" in dest_clean) or (orig_clean == dest_clean)

            # High-precision Uzbekistan domestic highway routing matrix
            route_db = {
                ("toshkent", "samarqand"): {
                    "distance_km": 386.2,
                    "transit_hours": 6.5,
                    "route_name": "M39 O'zbekiston Janubiy Aylanma Magistrali (Eng yaqin ichki tranzit)",
                    "route_corridor": "Toshkent → Yangiyo'l → Chinoz → Sirdaryo → Guliston → Yangiyer → Dashtobod → Zarbdor → Jizzax → Bulung'ur → Samarqand",
                    "domestic_only": True,
                    "foreign_borders": 0,
                    "road_quality": "4 polosali zamonaviy magistral"
                },
                ("toshkent", "buxoro"): {
                    "distance_km": 582.0,
                    "transit_hours": 8.5,
                    "route_name": "M39 + M37 Markaziy Magistral",
                    "route_corridor": "Toshkent → Guliston → Jizzax → Samarqand → Kattaqo'rg'on → Navoiy → Buxoro",
                    "domestic_only": True,
                    "foreign_borders": 0,
                    "road_quality": "M37 sement-beton tranzit yo'li"
                },
                ("toshkent", "andijon"): {
                    "distance_km": 348.5,
                    "transit_hours": 5.5,
                    "route_name": "A373 Kamchiq Dovoni Magistrali",
                    "route_corridor": "Toshkent → Ohangaron → Angren → Kamchiq dovoni → Qo'qon → Shahrixon → Andijon",
                    "domestic_only": True,
                    "foreign_borders": 0,
                    "road_quality": "Tog'li dovon tranziti (A373)"
                },
                ("toshkent", "farg'ona"): {
                    "distance_km": 325.0,
                    "transit_hours": 5.2,
                    "route_name": "A373 Kamchiq Dovoni Magistrali",
                    "route_corridor": "Toshkent → Ohangaron → Angren → Kamchiq dovoni → Qo'qon → Marg'ilon → Farg'ona",
                    "domestic_only": True,
                    "foreign_borders": 0,
                    "road_quality": "A373 / 4L ekspress tranzit"
                },
                ("toshkent", "qarshi"): {
                    "distance_km": 455.0,
                    "transit_hours": 7.2,
                    "route_name": "M39 + A378 Janubiy Koridor",
                    "route_corridor": "Toshkent → Guliston → Jizzax → Samarqand aylanma → Qarshi",
                    "domestic_only": True,
                    "foreign_borders": 0,
                    "road_quality": "M39 / A378 Janubiy koridor"
                }
            }

            key = (orig_clean, dest_clean)
            rev_key = (dest_clean, orig_clean)
            if is_intra_city:
                route_calc = {
                    "distance_km": 16.5,
                    "transit_hours": 0.8,
                    "route_name": "Shahar Ichki Tezkor Yo'nalishi",
                    "route_corridor": f"{origin} saralash punkti → {dest} manzili (To'g'ridan-to'g'ri yetkazish)",
                    "domestic_only": True,
                    "foreign_borders": 0,
                    "road_quality": "Shahar ichki ko'chalari"
                }
            elif key in route_db:
                route_calc = route_db[key]
            elif rev_key in route_db:
                route_calc = route_db[rev_key]
            else:
                route_calc = {
                    "distance_km": 350.0,
                    "transit_hours": 6.0,
                    "route_name": f"{origin} - {dest} Hududiy Magistrali",
                    "route_corridor": f"{origin} Hub → Magistral Tranzit → {dest} Hub",
                    "domestic_only": True,
                    "foreign_borders": 0,
                    "road_quality": "Respublika ahamiyatidagi tranzit yo'li"
                }

            dist = route_calc["distance_km"]

            # Dynamic price calculation according to delivery service formula & route distance
            fargo_price = round((15000 + dist * 42 + weight * 2000) / 1000) * 1000
            emu_price = round((20000 + dist * 48 + weight * 3000) / 1000) * 1000
            bts_price = round((12000 + dist * 34 + weight * 1500) / 1000) * 1000
            uzpost_price = round((10000 + dist * 25 + weight * 1000) / 1000) * 1000

            rates = [
                {
                    "carrier_code": "fargo",
                    "carrier_name": "Fargo Express",
                    "service_name": "Standart Tranzit (M39 Express)",
                    "price_uzs": fargo_price,
                    "estimated_days": "1-2 kun" if dist > 40 else "Shu kunning o'zida",
                    "estimated_hours": route_calc["transit_hours"],
                    "cutoff_time": "18:00",
                    "is_recommended": True,
                    "badge": "Eng ommabop",
                    "features": ["Eshikkacha yetkazish", "SMS xabarnoma", "Sug'urta mavjud", f"Masofa: {dist} km"]
                },
                {
                    "carrier_code": "emu",
                    "carrier_name": "EMU Express Mail",
                    "service_name": "Tezkor Aviatsiya / Avto Ekspress",
                    "price_uzs": emu_price,
                    "estimated_days": "1 kun (Ertasi kuni)" if dist < 650 else "1-2 kun",
                    "estimated_hours": max(4.0, route_calc["transit_hours"] * 0.75),
                    "cutoff_time": "19:30",
                    "is_recommended": False,
                    "badge": "Eng tez",
                    "features": ["Ekspress topshirish", "Jonli tracking", "Maxsus qadoq", f"Masofa: {dist} km"]
                },
                {
                    "carrier_code": "bts",
                    "carrier_name": "BTS Express Cargo",
                    "service_name": "Ombordan-Omborga Kargo",
                    "price_uzs": bts_price,
                    "estimated_days": "2-3 kun",
                    "estimated_hours": route_calc["transit_hours"] * 1.5,
                    "cutoff_time": "17:00",
                    "is_recommended": False,
                    "badge": "Iqtisodiy kargo",
                    "features": ["Qulay narx", "Katta o'lchamli yuklar", "Ombor qabul punkti", f"Masofa: {dist} km"]
                },
                {
                    "carrier_code": "uzpost",
                    "carrier_name": "UzPost (O'zbekiston Pochtasi)",
                    "service_name": "Milliy Pochta Xizmati",
                    "price_uzs": uzpost_price,
                    "estimated_days": "3-4 kun",
                    "estimated_hours": route_calc["transit_hours"] * 2.0,
                    "cutoff_time": "16:00",
                    "is_recommended": False,
                    "badge": "Eng keng qamrov",
                    "features": ["O'zbekiston bo'ylab 900+ bo'limlar", "Hamyonbop yetkazish", f"Masofa: {dist} km"]
                }
            ]

            if is_intra_city or dist <= 40:
                yandex_price = round((14000 + dist * 950) / 1000) * 1000
                rates.insert(0, {
                    "carrier_code": "yandex",
                    "carrier_name": "Yandex Delivery",
                    "service_name": "Tezkor Kuryer / Moto",
                    "price_uzs": yandex_price,
                    "estimated_days": "1-2 soat",
                    "estimated_hours": 1.5,
                    "cutoff_time": "23:00",
                    "is_recommended": True,
                    "badge": "Shahar ichida eng tez",
                    "features": ["Shahar ichida 2 soatda", "Xaritada jonli kuryer", f"Masofa: {dist} km"]
                })

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "origin": origin,
                "destination": dest,
                "weight_kg": weight,
                "route_calculation": route_calc,
                "rates": rates
            }).encode('utf-8'))
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
                {"code": "uzpost", "name": "UzPost", "phone": "+998712335747"},
                {"code": "yandex", "name": "Yandex Delivery", "phone": "+998712003344"}
            ]
            self.wfile.write(json.dumps({"carriers": carriers}).encode('utf-8'))
            return

        # Documentation Redirect
        if parsed.path in ["/docs", "/v1/docs", "/documentation"]:
            self.send_response(302)
            self.send_header('Location', '/docs.html')
            self.end_headers()
            return

        # API: GET /health
        if parsed.path == "/health":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "service": "Shipping Middleware Service"}).encode('utf-8'))
            return

        # Otherwise serve static frontend
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)

        # API: POST /v1/shipments (Marketplace Books a Delivery with Courier via Engine)
        if parsed.path == "/v1/shipments":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))

            ext_order = data.get("external_order_no", f"ORD-{int(time.time())}")
            carrier_code = data.get("carrier_code", "fargo")
            carrier_names = {
                "fargo": "Fargo Express",
                "emu": "EMU Express Mail",
                "bts": "BTS Express Cargo",
                "uzpost": "UzPost",
                "yandex": "Yandex Delivery"
            }

            # Generate unique standard tracking code
            tracking_code = f"UZ{int(time.time()*1000)%100000000000:011d}"
            sender_city = data.get("sender_city", "Toshkent")
            recipient_city = data.get("recipient_city", "Samarqand")
            recipient_hub = data.get("recipient_address", f"{recipient_city} shahar, Markaziy qabul hududi")

            new_shipment = {
                "tracking_code": tracking_code,
                "external_order_no": ext_order,
                "marketplace_id": data.get("marketplace_id", "olx"),
                "carrier": {
                    "code": carrier_code,
                    "name": carrier_names.get(carrier_code, carrier_code.upper()),
                    "support_phone": "+998712000000"
                },
                "status": "ORDER_CREATED",
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "eta": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 86400 * 2)),
                "current_location": {
                    "city": sender_city,
                    "hub": f"{sender_city} qabul filiali",
                    "lat": 41.2268,
                    "lng": 69.2198,
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                },
                "route": {
                    "origin": {"city": sender_city, "hub": f"{sender_city} Jo'natuvchi manzili", "lat": 41.2268, "lng": 69.2198},
                    "destination": {"city": recipient_city, "hub": recipient_hub, "lat": 39.6542, "lng": 66.9597},
                    "waypoints": [
                        {"city": sender_city, "label": f"{sender_city} Saralash Markazi", "lat": 41.2268, "lng": 69.2198, "is_passed": True},
                        {"city": "Yangiyo'l", "label": "M39 Yangiyo'l nazorati", "lat": 41.1167, "lng": 69.0500, "is_passed": False},
                        {"city": "Chinoz", "label": "Chinoz daryo o'tish punkti", "lat": 40.9411, "lng": 68.7594, "is_passed": False},
                        {"city": "Jizzax", "label": "Jizzax M39 tranzit nazorati", "lat": 40.1158, "lng": 67.8422, "is_passed": False},
                        {"city": recipient_city, "label": f"{recipient_city} Qabul markazi", "lat": 39.6542, "lng": 66.9597, "is_passed": False}
                    ]
                },
                "courier": {
                    "name": "Jasur Aliyev",
                    "phone": "+998 90 123 45 67",
                    "vehicle_type": "truck"
                },
                "item": data.get("item", {
                    "title": "Apple MacBook Pro 14\" (M3 Pro 18/512GB)",
                    "price": 21500000,
                    "currency": "UZS",
                    "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=240&q=80",
                    "payment_status": "To'langan (Click / Payme)"
                }),
                "inspection_photos": [
                    {
                        "url": data.get("item", {}).get("image_url", "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=800&q=80"),
                        "thumb": data.get("item", {}).get("image_url", "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=300&q=80"),
                        "caption_uz": f"{data.get('item', {}).get('title', 'Tovar')} ombor qabuli tekshiruvi (验货照)",
                        "caption_ru": "Проверка товара на складе (验货照)",
                        "caption_en": "Inspection photo of parcel at carrier hub"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=800&q=80",
                        "thumb": "https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=300&q=80",
                        "caption_uz": "Standart himoya qutisi butunligi tekshirildi (Fargo Hub)",
                        "caption_ru": "Защитная упаковка проверена",
                        "caption_en": "Standard protective packing verified"
                    }
                ],
                "timeline": [
                    {
                        "code": "ORDER_CREATED",
                        "title_uz": "Buyurtma qabul qilindi",
                        "title_ru": "Заказ оформлен",
                        "title_en": "Order Placed",
                        "description_uz": f"Buyurtma {carrier_names.get(carrier_code, 'Kuryer')} tizimiga muvaffaqiyatli uzatildi. Kuryer jo'natmani qabul qilishga yo'l oldi.",
                        "description_ru": f"Заказ успешно передан в службу {carrier_names.get(carrier_code, 'курьера')}.",
                        "description_en": f"Order registered with {carrier_names.get(carrier_code, 'courier')}.",
                        "location_name": sender_city,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    }
                ]
            }

            shipments[tracking_code] = new_shipment

            self.send_response(201)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "shipment_id": f"shp_{int(time.time())}",
                "tracking_code": tracking_code,
                "external_order_no": ext_order,
                "carrier": new_shipment["carrier"],
                "tracking_embed_url": f"/?code={tracking_code}&brand={data.get('marketplace_id', 'olx')}&embed=true",
                "shipment": new_shipment
            }).encode('utf-8'))
            return

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
                            s["status"] = "DELIVERED"
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

        # API: POST /v1/carriers/{code}/webhook (Couriers Push Real Events to Engine)
        match = re.match(r"^/v1/carriers/([A-Za-z0-9_-]+)/webhook$", parsed.path)
        if match:
            carrier = match.group(1)
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))

            code = data.get("tracking_code")
            raw_status = data.get("raw_status", "in_transit").lower()

            # Normalize carrier internal status to UZ-LTS
            status_map = {
                "picked_up": ("PICKED_UP", "Kuryer jo'natuvchidan qabul qildi", "Курьер забрал у отправителя"),
                "hub_in": ("ORIGIN_HUB_IN", "Saralash markaziga yetib keldi", "Прибыло в сортировочный центр"),
                "in_transit": ("IN_TRANSIT", "Shaharlararo yo'lda harakatlanmoqda", "Движется между городами"),
                "dest_hub": ("DEST_HUB_IN", "Mintaqaviy saralash markaziga yetib keldi", "Прибыло в региональный хаб"),
                "out_for_delivery": ("OUT_FOR_DELIVERY", "Kuryer xaridor tomon yo'lga chiqdi", "Курьер выехал к покупателю"),
                "delivered": ("DELIVERED", "Mijozga muvaffaqiyatli topshirildi", "Успешно доставлено покупателю")
            }

            norm_status, title_uz, title_ru = status_map.get(raw_status, ("IN_TRANSIT", "Holat yangilandi", "Статус обновлен"))

            if code in shipments:
                s = shipments[code]
                s["status"] = norm_status
                if data.get("city"):
                    s["current_location"]["city"] = data.get("city")
                if data.get("hub_name"):
                    s["current_location"]["hub"] = data.get("hub_name")
                if data.get("lat") and data.get("lng"):
                    s["current_location"]["lat"] = float(data.get("lat"))
                    s["current_location"]["lng"] = float(data.get("lng"))

                note = data.get("note") or title_uz
                s["timeline"].insert(0, {
                    "code": norm_status,
                    "title_uz": title_uz,
                    "title_ru": title_ru,
                    "title_en": norm_status.replace('_', ' ').title(),
                    "description_uz": f"{note}. Kuryer: {s.get('courier', {}).get('name', 'Jasur Aliyev')}.",
                    "description_ru": f"{note}. Курьер: {s.get('courier', {}).get('name', 'Джасур Алиев')}.",
                    "description_en": f"{note}.",
                    "location_name": data.get("hub_name", s["current_location"]["hub"]),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                })

                # Simulated outbound webhook dispatched to the marketplace
                marketplace_webhook_payload = {
                    "event": "shipment.status_changed",
                    "tracking_code": code,
                    "external_order_no": s["external_order_no"],
                    "marketplace_id": s["marketplace_id"],
                    "carrier_code": carrier,
                    "raw_status": raw_status,
                    "standardized_status": norm_status,
                    "title_uz": title_uz,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "normalized_status": norm_status,
                    "dispatched_to_marketplace_webhook": marketplace_webhook_payload,
                    "updated_shipment": s
                }).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
            return

        # SUPPLY SIDE API: POST /v1/carrier/manifests (Couriers Query & Acknowledge Pickup Manifests)
        if parsed.path == "/v1/carrier/manifests":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            data = json.loads(body.decode('utf-8')) if body else {}

            carrier_code = data.get("carrier_code", "fargo").lower()
            carrier_shipments = [s for s in shipments.values() if s.get("carrier", {}).get("code") == carrier_code]

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "carrier_code": carrier_code,
                "manifest_id": f"MNF-{carrier_code.upper()}-{int(time.time())}",
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "total_parcels": len(carrier_shipments),
                "parcels": carrier_shipments
            }).encode('utf-8'))
            return

        # SUPPLY SIDE API: POST /v1/carrier/events (Couriers Push Checkpoint Telemetry to Engine)
        if parsed.path == "/v1/carrier/events":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))

            code = data.get("tracking_code")
            raw_status = data.get("status", "IN_TRANSIT").upper()
            checkpoint_name = data.get("checkpoint_name", "Markaziy Saralash Punkti")

            if code in shipments:
                s = shipments[code]
                s["status"] = raw_status
                if data.get("lat") and data.get("lng"):
                    s["current_location"]["lat"] = float(data.get("lat"))
                    s["current_location"]["lng"] = float(data.get("lng"))
                if data.get("city"):
                    s["current_location"]["city"] = data.get("city")
                s["current_location"]["hub"] = checkpoint_name
                s["current_location"]["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

                s["timeline"].insert(0, {
                    "code": raw_status,
                    "title_uz": f"Kuryer voqeasi: {checkpoint_name}",
                    "title_ru": f"Событие курьера: {checkpoint_name}",
                    "title_en": f"Courier Event: {checkpoint_name}",
                    "description_uz": data.get("description", f"Jo'natma {checkpoint_name} nazoratidan o'tkazildi."),
                    "description_ru": data.get("description", f"Посылка прошла пункт {checkpoint_name}."),
                    "description_en": data.get("description", f"Package scanned at {checkpoint_name}."),
                    "location_name": checkpoint_name,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                })

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "tracking_code": code, "status": s["status"]}).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(json.dumps({"error": True, "message": "Shipment not found"}).encode('utf-8'))
            return

        # SUPPLY SIDE API: POST /v1/carrier/inspections (Couriers Upload Hub Quality Inspection Photos)
        if parsed.path == "/v1/carrier/inspections":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))

            code = data.get("tracking_code")
            photo_url = data.get("photo_url")
            caption_uz = data.get("caption_uz", "Omborda tovar qadog'i va butunligi tekshirildi (验货照)")

            if code in shipments and photo_url:
                s = shipments[code]
                if "inspection_photos" not in s:
                    s["inspection_photos"] = []
                s["inspection_photos"].insert(0, {
                    "url": photo_url,
                    "thumb": photo_url,
                    "caption_uz": caption_uz,
                    "caption_ru": data.get("caption_ru", caption_uz),
                    "caption_en": data.get("caption_en", caption_uz)
                })

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "inspection_count": len(s["inspection_photos"])}).encode('utf-8'))
            else:
                self.send_response(400)
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
