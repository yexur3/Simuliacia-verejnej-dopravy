import json
from pathlib import Path

import requests


URL = (
    "https://opendata.banskabystrica.sk"
    "/api/datasets/v1/public-transport/stops/list"
)

# Зберігаємо дані поруч зі скриптом незалежно від папки запуску.
BASE_DIR = Path(__file__).resolve().parent
OUT_FILE = BASE_DIR / "data" / "departures.json"
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Завантажуємо накопичені записи.
if OUT_FILE.exists():
    with OUT_FILE.open(encoding="utf-8") as f:
        collected = json.load(f)
else:
    collected = {}

print("Запитую дані API...", flush=True)

response = requests.post(URL, json={}, timeout=30)
response.raise_for_status()
stops = response.json()

new_count = 0
skipped_count = 0

for stop in stops:
    if stop is None:
        continue

    # Якщо departures дорівнює null, використовуємо порожній список.
    departures = stop["departures"] or []

    for dep in departures:
        # У відповіді API можуть бути порожні елементи.
        if dep is None:
            skipped_count += 1
            continue

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

# Спочатку записуємо тимчасовий файл, потім замінюємо основний.
temp_file = OUT_FILE.with_suffix(".tmp")

with temp_file.open("w", encoding="utf-8") as f:
    json.dump(collected, f, ensure_ascii=False, indent=2)

temp_file.replace(OUT_FILE)

print(f"Нових: {new_count}, всього записів: {len(collected)}")
print(f"Пропущено порожніх відправлень: {skipped_count}")
print(f"Збережено: {OUT_FILE}")