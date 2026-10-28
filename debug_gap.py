import json
import math
from collections import defaultdict
from datetime import datetime

from reconstruct import merge_order, to_seconds

with open("stops.json", encoding="utf-8") as f:
    stops = json.load(f)
with open("data/departures.json", encoding="utf-8") as f:
    departures = json.load(f)

# Координати в метрах, щоб відстані й швидкість були реальними
lat0 = sum(s["position"]["coordinates"][1] for s in stops) / len(stops)

def to_m(lon, lat):
    return lon * 111320 * math.cos(math.radians(lat0)), lat * 110540

pos = {s["stopId"]: to_m(*s["position"]["coordinates"]) for s in stops}
name = {s["stopId"]: s["name"] for s in stops}

known_by_trip = defaultdict(dict)
trip_group = {}
line_name = {}
for d in departures.values():
    if d["stopId"] in pos and d["scheduleTime"] and d["tripId"]:
        known_by_trip[d["tripId"]][d["stopId"]] = to_seconds(d["scheduleTime"])
        trip_group[d["tripId"]] = (d["routeId"], d["direction"])
        line_name[(d["routeId"], d["direction"])] = d["routeShortName"]

groups = defaultdict(list)
for tid, g in trip_group.items():
    groups[g].append(tid)

worst = None
for g, tids in groups.items():
    tids.sort(key=lambda t: len(known_by_trip[t]), reverse=True)
    seqs = [[s for s, _ in sorted(known_by_trip[t].items(), key=lambda kv: kv[1])]
            for t in tids]
    order = merge_order(seqs)
    idx = {s: i for i, s in enumerate(order)}
    cum = [0.0]
    for a, b in zip(order, order[1:]):
        cum.append(cum[-1] + math.dist(pos[a], pos[b]))
    for tid in tids:
        pts = sorted((idx[s], t, s) for s, t in known_by_trip[tid].items() if s in idx)
        for (i1, t1, s1), (i2, t2, s2) in zip(pts, pts[1:]):
            dt = t2 - t1
            dist = cum[i2] - cum[i1]
            if dt > 0 and dist > 0:
                v = dist / dt * 3.6
                if worst is None or v > worst[0]:
                    worst = (v, g, tid, s1, s2, order, idx, i1, i2, dt, dist)

v, g, tid, s1, s2, order, idx, i1, i2, dt, dist = worst
print(f"Лінія {line_name[g]}, напрямок: {g[1]}")
print(f"Відомі сусідні зупинки: {name[s1]} -> {name[s2]}")
print(f"За часом між ними {dt:.0f} с, а за порядком лінії це {i2 - i1} зупинок "
      f"і {dist:.0f} м ({v:.0f} км/год)")

print("\nУсі відомі зупинки цього рейсу (за часом):")
for s, t in sorted(known_by_trip[tid].items(), key=lambda kv: kv[1]):
    hhmm = datetime.fromtimestamp(t).strftime("%H:%M:%S")
    place = idx.get(s, "нема")
    print(f"  {hhmm}  місце в порядку лінії: {place!s:>4}  {name[s]}")

print("\nЗупинки в порядку лінії між ними:")
for i in range(i1, i2 + 1):
    print(f"  {i:>3}  {name[order[i]]}")