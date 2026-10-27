#!/usr/bin/env python3
"""
UzTrack (UZ-LTS) - Tier 2 Logistics Dispatch Bulk CSV/Excel Importer
Allows logistics companies without developer teams (e.g. 1C exports, Excel sheets)
to batch upload tracking checkpoints to UzTrack in seconds.
"""

import csv
import json
import sys
import time
import urllib.request
import urllib.error

API_URL = "http://localhost:8080/v1/carriers"

def import_csv(file_path: str, carrier_code: str = "generic"):
    print(f"[INFO] Starting batch import for carrier '{carrier_code}' from: {file_path}")
    success_count = 0
    fail_count = 0

    endpoint = f"{API_URL}/{carrier_code}/webhook"

    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            payload = {
                "tracking_code": row.get("tracking_code", "").strip(),
                "raw_status": row.get("status", "").strip(),
                "hub_name": row.get("hub_name", "").strip(),
                "city": row.get("city", "").strip(),
                "lat": float(row.get("lat", 0.0) or 0.0),
                "lng": float(row.get("lng", 0.0) or 0.0),
                "note": row.get("note", "").strip(),
            }

            if not payload["tracking_code"] or not payload["raw_status"]:
                print(f"[SKIP] Invalid row: {row}")
                fail_count += 1
                continue

            try:
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(endpoint, data=data, headers={'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        res = json.loads(resp.read().decode('utf-8'))
                        print(f"[SUCCESS] {payload['tracking_code']} -> Normalized: {res.get('normalized_status')}")
                        success_count += 1
                    else:
                        print(f"[ERROR] Failed for {payload['tracking_code']}: HTTP {resp.status}")
                        fail_count += 1
            except urllib.error.URLError as e:
                print(f"[ERROR] Network error for {payload['tracking_code']}: {e}")
                fail_count += 1

    print("\n================ Import Summary ================")
    print(f"Total Processed: {success_count + fail_count}")
    print(f"Successful:      {success_count}")
    print(f"Failed:          {fail_count}")
    print("================================================")

if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    if len(sys.argv) < 2:
        print("Usage: python bulk_importer.py <file.csv> [carrier_code]")
        print("Example: python bulk_importer.py sample_dispatch.csv bts")
        sys.exit(1)

    carrier = sys.argv[2] if len(sys.argv) > 2 else "fargo"
    import_csv(sys.argv[1], carrier)
