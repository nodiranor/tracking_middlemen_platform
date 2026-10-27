#!/usr/bin/env python3
"""
UzTrack (UZ-LTS) - Tier 3 Courier & Regional Hub Telegram Bot
Allows logistics couriers and small delivery services across Uzbekistan
to update delivery statuses and stream live GPS with zero IT infrastructure.
"""

import json
import os
import sys
import urllib.request
import urllib.error

API_BASE_URL = os.getenv("UZTRACK_API_URL", "http://localhost:8080")

class CourierBotHandler:
    def __init__(self, api_url=API_BASE_URL):
        self.api_url = api_url

    def get_tracking(self, code: str):
        url = f"{self.api_url}/v1/tracks/{code}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'UzTrack-TelegramBot/1.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode('utf-8'))
        except urllib.error.URLError as e:
            print(f"[Error] Failed to fetch {code}: {e}")
        return None

    def post_status_update(self, carrier: str, tracking_code: str, raw_status: str, hub: str, city: str, lat: float = 0.0, lng: float = 0.0, note: str = ""):
        url = f"{self.api_url}/v1/carriers/{carrier}/webhook"
        payload = {
            "tracking_code": tracking_code,
            "raw_status": raw_status,
            "hub_name": hub,
            "city": city,
            "lat": lat,
            "lng": lng,
            "note": note
        }
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode('utf-8'))
        except urllib.error.URLError as e:
            print(f"[Error] Webhook failed: {e}")
        return None

    def render_courier_menu(self, code: str):
        data = self.get_tracking(code)
        if not data:
            return f"[ERROR] Trek raqami topilmadi: {code}"

        status = data.get("status", "NOMA'LUM")
        city = data.get("current_location", {}).get("city", "Noma'lum")
        
        menu = f"""
[JO'NATMA] Code: {code}
[TASHUVCHI] {data.get('carrier', {}).get('name', 'Fargo Express')}
[MANZIL] Joylashuv: {city}
[HOLAT] {status}

Statusni yangilash:
[1] Saralash markazida (ORIGIN_HUB_IN)
[2] Shaharlararo yo'lda (IN_TRANSIT)
[3] Manzil saralash markazida (DEST_HUB_IN)
[4] Kuryer yetkazmoqda (OUT_FOR_DELIVERY)
[5] Qabul qiluvchiga topshirildi (DELIVERED)
[6] Jonli GPS lokatsiyani yangilash
"""
        return menu

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    bot = CourierBotHandler()
    print("==================================================================")
    print("  UzTrack Telegram Courier Scanner & Checkpoint Updater (CLI Mock)")
    print("==================================================================")
    sample_code = "UZ77019283401"
    print(bot.render_courier_menu(sample_code))
    
    print("Simulating status change to OUT_FOR_DELIVERY with courier GPS...")
    res = bot.post_status_update(
        carrier="fargo",
        tracking_code=sample_code,
        raw_status="OUT_FOR_DELIVERY",
        hub="Samarqand Markaziy PVZ",
        city="Samarqand",
        lat=39.6542,
        lng=66.9597,
        note="Kuryer Jasur Aliyev jo'natmani topshirish uchun yo'lga chiqdi."
    )
    print("Result from UzTrack API:", res)
