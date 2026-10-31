import json
import math
import os
from collections import defaultdict

from reconstruct import build_trips, trip_completeness
from typical_day import make_typical_day

MIN_COMP = 0.5      # те саме, що MIN_TRIP_COMPLETENESS у simulation.py
SLOW_KMH = 3.0      # повільніше за це вважаємо "стоїть"

with open("stops.json", encoding="utf-8") as f:
    stops = json.load(f)
with open("data/departures.json", encoding="utf-8") as f:
    departures = json.load(f)
paths = {}
if os.path.exists("paths.json"):
    with open("paths.json", encoding="utf-8") as f:
        paths = json.load(f)

lat0 = sum(s["position"]["coordinates"][1] for s in stops) / len(stops)
KX, KY = 111320 * math.cos(math.radians(lat0)), 110540

def to_m(lon, lat):
    return lon * KX, lat * KY

pos_m = {s["stopId"]: to_m(*s["position"]["coordinates"]) for s in stops}
name = {s["stopId"]: s["name"] for s in stops}
route = {d["tripId"]: d.get("routeShortName", "?") for d in departures.values() if d.get("tripId")}

trips, trip_type = build_trips(departures, pos_m)
trips, trip_type = make_typical_day(trips, trip_type, trip_completeness(departures), MIN_COMP)

def seg_length(a, b):
    """Довжина шляху між зупинками: по дорозі (paths.json), якщо є, інакше по прямій."""
    lo, hi = (a, b) if a <= b else (b, a)
    raw = paths.get(f"{lo}|{hi}")
    if raw:
        pts = [to_m(lon, lat) for lon, lat in raw]
        return sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))
    return math.dist(pos_m[a], pos_m[b])

total = slow = same_place = long_slow = 0.0
per_route = defaultdict(lambda: [0.0, 0.0])    # лінія -> [весь час, повільний час]
rows = []
for tid, items in trips.items():
    r = route.get(tid.split("#")[0].rstrip("~"), "?")
    for (t1, a), (t2, b) in zip(items, items[1:]):
        dt = t2 - t1
        if dt <= 0 or a == b:
            continue
        dist = seg_length(a, b)
        v = dist / dt * 3.6
        total += dt
        per_route[r][0] += dt
        if v < SLOW_KMH:
            slow += dt
            per_route[r][1] += dt
            if dist < 60:
                same_place += dt
            if dt >= 180:
                long_slow += dt
                rows.append((dt, r, name[a], name[b], dist, v))

print(f"Рейсів у типовому дні: {len(trips)}")
print(f"Час руху всіх рейсів: {total / 3600:.0f} год")
print(f"З нього «стоїть» (швидкість < {SLOW_KMH:g} км/год): {slow / 3600:.1f} год  ({slow / total:.0%})")
print(f"  з них між зупинками на одному місці (< 60 м): {same_place / 3600:.1f} год")
print(f"  з них довгі відрізки (>= 3 хв): {long_slow / 3600:.1f} год")

print("\nЛінії з найбільшою часткою «стояння»:")
ranked = sorted(per_route.items(), key=lambda kv: kv[1][1], reverse=True)[:8]
for r, (tot, sl) in ranked:
    print(f"  лінія {r}: {sl / 3600:.1f} год із {tot / 3600:.1f} год ({sl / tot:.0%})")

print("\nНайдовші «стояння» (відрізок >= 3 хв):")
for dt, r, a, b, dist, v in sorted(rows, reverse=True)[:12]:
    print(f"  лінія {r}: {a} -> {b}: {dist:.0f} м за {dt / 60:.0f} хв ({v:.1f} км/год)")