import json
from collections import defaultdict

from reconstruct import collect_runs

with open("stops.json", encoding="utf-8") as f:
    stops = json.load(f)
with open("data/departures.json", encoding="utf-8") as f:
    departures = json.load(f)

name = {s["stopId"]: s["name"] for s in stops}
by_name = defaultdict(set)
for sid, nm in name.items():
    by_name[nm.strip().lower()].add(sid)

runs, group, _ = collect_runs(departures)

# лінія+напрямок -> усі зупинки, які взагалі бачили в рейсах цієї групи
seen = defaultdict(set)
for rid, g in group.items():
    seen[g] |= set(runs[rid])

total = matchable = observed = 0
missing_examples = []
for (route, direction), stops_seen in seen.items():
    total += 1
    target = (direction or "").strip().lower()
    if target not in by_name:
        continue                       # назва напряму не збігається з назвою жодної зупинки
    matchable += 1
    if by_name[target] & stops_seen:
        observed += 1
    elif len(missing_examples) < 8:
        missing_examples.append((route, direction))

print(f"Груп «лінія + напрямок»: {total}")
print(f"  назва напряму збігається з назвою якоїсь зупинки: {matchable}")
print(f"  з них кінцеву зупинку взагалі видно в даних:      {observed}")
print(f"  з них кінцевої зупинки в даних НЕМАЄ:             {matchable - observed}")
if matchable and observed / matchable < 0.2:
    print("\nВисновок: API, схоже, не віддає кінцеву зупинку. Її треба добудовувати за назвою напряму.")
elif matchable and observed / matchable > 0.8:
    print("\nВисновок: кінцеві зупинки в даних є, причина обірваних рейсів інша.")
else:
    print("\nВисновок: змішана картина, частину кінцевих видно, частину ні.")
if missing_examples:
    print("\nПриклади груп без кінцевої в даних (лінія, напрям):")
    for r, d in missing_examples:
        print(f"  {r} -> {d}")
nomatch = total - matchable
if nomatch:
    print(f"\nУ {nomatch} груп назва напряму не збігається з жодною зупинкою (там добудова кінцевої не спрацює).")