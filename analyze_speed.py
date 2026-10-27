import json
import math

from reconstruct import build_trips

with open("stops.json", encoding="utf-8") as f:
    stops = json.load(f)
with open("data/departures.json", encoding="utf-8") as f:
    departures = json.load(f)

# Координати в метрах (а не в пікселях), щоб швидкість була в км/год
lat0 = sum(s["position"]["coordinates"][1] for s in stops) / len(stops)

def to_m(lon, lat):
    return lon * 111320 * math.cos(math.radians(lat0)), lat * 110540

pos = {s["stopId"]: to_m(*s["position"]["coordinates"]) for s in stops}
name = {s["stopId"]: s["name"] for s in stops}

trips, _ = build_trips(departures, pos)

rows = []      # (швидкість км/год, відстань м, секунди, зупинка A, зупинка B)
total = 0
instant = 0    # сусідні зупинки з однаковим часом
for items in trips.values():
    for (t1, a), (t2, b) in zip(items, items[1:]):
        if a == b:
            continue
        total += 1
        dist = math.dist(pos[a], pos[b])
        dt = t2 - t1
        if dt <= 0:
            instant += 1
            if dist > 200:
                rows.append((float("inf"), dist, dt, a, b))
            continue
        rows.append((dist / dt * 3.6, dist, dt, a, b))

fast = [r for r in rows if r[0] > 60]
print("Всього відрізків:", total)
print("З однаковим часом на сусідніх зупинках:", instant)
print("Відрізків із прямою швидкістю понад 60 км/год:", len(fast))
print("\\nНайгірші 10:")
for v, dist, dt, a, b in sorted(rows, key=lambda r: r[0], reverse=True)[:10]:
    speed = "миттєво" if v == float("inf") else f"{v:.0f} км/год"
    print(f"  {name[a]} -> {name[b]}: {dist:.0f} м за {dt:.0f} с ({speed})")