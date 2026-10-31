import json
import os
import time
from datetime import datetime
import traceback

import requests

URL = "https://opendata.banskabystrica.sk/api/datasets/v1/public-transport/stops/list"
OUT_FILE = "data/departures.json"
INTERVAL_MIN = 10

os.makedirs("data", exist_ok=True)

if os.path.exists(OUT_FILE):
    with open(OUT_FILE, encoding="utf-8") as f:
        collected = json.load(f)
else:
    collected = {}

while True:
    try:
        r = requests.post(URL, json={}, timeout=30)
        r.raise_for_status()
        stops = r.json()

        if not isinstance(stops, list):
            print("Незвична відповідь API:", str(stops)[:300])
            stops = []

        new_count = 0
        for stop in stops:
            if not stop:
                continue
            for dep in (stop.get("departures") or []):
                if not dep:
                    continue
                key = f'{dep.get("tripId")}|{stop.get("stopId")}|{dep.get("scheduleTime")}'
                if key not in collected:
                    new_count += 1
                collected[key] = {
                    "tripId": dep.get("tripId"),
                    "stopId": stop.get("stopId"),
                    "routeId": dep.get("routeId"),
                    "routeShortName": dep.get("routeShortName"),
                    "vehicleType": dep.get("vehicleType"),
                    "direction": dep.get("direction"),
                    "scheduleTime": dep.get("scheduleTime"),
                    "realTime": dep.get("realTime"),
                }

        with open(OUT_FILE, "w", encoding="utf-8") as f:
            json.dump(collected, f, ensure_ascii=False)

        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] нових: {new_count}, всього записів: {len(collected)}")

    except Exception:
        traceback.print_exc()  # повна помилка з номером рядка

    time.sleep(INTERVAL_MIN * 60)