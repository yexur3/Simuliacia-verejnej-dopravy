import json
import time

import requests

with open("stops.json", encoding="utf-8") as f:
    stops = json.load(f)
lons = [s["position"]["coordinates"][0] for s in stops]
lats = [s["position"]["coordinates"][1] for s in stops]
PAD = 0.01
south, north = min(lats) - PAD, max(lats) + PAD
west, east = min(lons) - PAD, max(lons) + PAD
BBOX = f"({south},{west},{north},{east})"

# Кілька дзеркал: якщо один перевантажений, пробуємо наступний
MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

MAJOR_TYPES = "motorway|trunk|primary|secondary|tertiary"
MINOR_TYPES = "unclassified|residential|living_street"


def run_query(types):
    query = f"""
[out:json][timeout:60];
way["highway"~"^({types})(_link)?$"]{BBOX};
out geom;
"""
    for url in MIRRORS:
        try:
            print("  запит до", url)
            r = requests.post(
                url, data={"data": query},
                timeout=(15, 180),   # 15 с на підключення, 180 с на відповідь
                headers={"User-Agent": "mhd-simulation-student-project"},
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print("  не вийшло:", type(e).__name__)
            time.sleep(2)
    return None


def to_roads(data, major):
    roads = []
    for el in data["elements"]:
        if el["type"] == "way" and "geometry" in el:
            roads.append({
                "major": major,
                "pts": [[p["lon"], p["lat"]] for p in el["geometry"]],
            })
    return roads


roads = []

print("1/2 головні дороги")
data = run_query(MAJOR_TYPES)
if data is None:
    raise SystemExit("Жоден сервер не відповів навіть на малий запит. Спробуй пізніше.")
roads += to_roads(data, True)
print("  головних:", len(roads))

# Зберігаємо одразу, щоб навіть неповний результат не пропав
with open("roads.json", "w", encoding="utf-8") as f:
    json.dump(roads, f)

print("2/2 дрібні вулиці")
data = run_query(MINOR_TYPES)
if data is None:
    print("  дрібні вулиці не завантажилися, лишаємо тільки головні")
else:
    roads += to_roads(data, False)
    with open("roads.json", "w", encoding="utf-8") as f:
        json.dump(roads, f)

print("Усього доріг у файлі:", len(roads))