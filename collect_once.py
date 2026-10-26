import json
import os
import requests

URL = "https://opendata.banskabystrica.sk/api/datasets/v1/public-transport/stops/list"
OUT_FILE = "data/departures.json"

os.makedirs("data", exist_ok=True)

# Підхоплюємо те, що вже накопичено в попередніх запусках
if os.path.exists(OUT_FILE):
    with open(OUT_FILE, encoding="utf-8") as f:
        collected = json.load(f)
else:
    collected = {}

r = requests.post(URL, json={}, timeout=30)
r.raise_for_status()  # якщо API не відповіло, запуск стане червоним і ми це побачимо
stops = r.json()

new_count = 0
for stop in stops:
    for dep in stop["departures"]:
        key = f'{dep["tripId"]}|{stop["stopId"]}'
        if key not in collected:
            new_count += 1
        collected[key] = {
            "tripId": dep["tripId"],
            "stopId": stop["stopId"],
            "routeId": dep["routeId"],
            "routeShortName": dep["routeShortName"],
            "vehicleType": dep["vehicleType"],
            "direction": dep["direction"],
            "scheduleTime": dep["scheduleTime"],
            "realTime": dep["realTime"],
        }

with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(collected, f, ensure_ascii=False)

print(f"нових: {new_count}, всього записів: {len(collected)}")