import json
import math
import os

from reconstruct import build_trips
from roadgraph import RoadGraph

PATHS_FILE = "paths.json"
SNAP_DIST = 150        # зупинка далі ніж за стільки метрів від дороги не прилипає
DETOUR_LIMIT = 3       # шлях по дорогах не довший за 3x пряму (+300 м запасу)

with open("stops.json", encoding="utf-8") as f:
    stops = json.load(f)
with open("data/departures.json", encoding="utf-8") as f:
    departures = json.load(f)
with open("roads.json", encoding="utf-8") as f:
    roads = json.load(f)

lat0 = sum(s["position"]["coordinates"][1] for s in stops) / len(stops)
print("Будуємо граф доріг...")
graph = RoadGraph(roads, lat0)
print("  вершин:", len(graph.lonlat))

lonlat = {s["stopId"]: tuple(s["position"]["coordinates"]) for s in stops}
pos_m = {sid: graph.to_xy(*ll) for sid, ll in lonlat.items()}

# Які пари сусідніх зупинок взагалі зустрічаються в рейсах
trips, _ = build_trips(departures, pos_m)
pairs = set()
for items in trips.values():
    for (_, a), (_, b) in zip(items, items[1:]):
        if a != b:
            pairs.add(tuple(sorted((a, b))))
print("Унікальних пар зупинок:", len(pairs))

# Уже пораховане не рахуємо вдруге
paths = {}
if os.path.exists(PATHS_FILE):
    with open(PATHS_FILE, encoding="utf-8") as f:
        paths = json.load(f)
todo = [p for p in pairs if f"{p[0]}|{p[1]}" not in paths]
print("Треба порахувати:", len(todo))

# Прив'язуємо кожну зупинку до найближчої точки дороги
snap = {sid: graph.nearest(*ll, max_dist=SNAP_DIST) for sid, ll in lonlat.items()}
print("Зупинок, що не прилипли до доріг:", sum(1 for v in snap.values() if v is None))

found = 0
for n, (a, b) in enumerate(todo, 1):
    key = f"{a}|{b}"
    result = None
    na, nb = snap.get(a), snap.get(b)
    if na is not None and nb is not None and na != nb:
        direct = math.dist(pos_m[a], pos_m[b])
        res = graph.path(na, nb, limit=DETOUR_LIMIT * direct + 300)
        if res:
            pts, _ = res
            # Додаємо самі зупинки на кінцях, щоб точка доїжджала до них
            result = [list(lonlat[a])] + [list(p) for p in pts] + [list(lonlat[b])]
            found += 1
    paths[key] = result     # None означає «малюємо по прямій»
    if n % 200 == 0:
        print(f"  {n}/{len(todo)}")

with open(PATHS_FILE, "w", encoding="utf-8") as f:
    json.dump(paths, f)
print(f"Готово. Знайдено по дорогах: {found} із {len(todo)}; решта піде по прямій.")