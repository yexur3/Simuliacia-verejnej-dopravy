import json
import os
from collections import defaultdict
from datetime import datetime, timedelta

PATH = "data/departures.json"
LOW = 0.6          # середня повнота нижче цього значення вважаємо провалом
BAR = 20           # довжина смужки в таблиці


def parse(iso):
    """'2026-10-27T08:15:00.000Z' -> місцевий час."""
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone()


with open(PATH, encoding="utf-8") as f:
    departures = json.load(f)

# Останнє оновлення файлу = час останнього опитування збирачем
last_snapshot = datetime.fromtimestamp(os.path.getmtime(PATH)).astimezone()

# 1. tripId -> {stopId: час}; і до якої лінії/напрямку належить рейс
known = defaultdict(dict)
group = {}
for d in departures.values():
    if d.get("tripId") and d.get("scheduleTime") and d.get("stopId"):
        known[d["tripId"]][d["stopId"]] = parse(d["scheduleTime"])
        group[d["tripId"]] = (d.get("routeId"), d.get("direction"))

# 2. Скільки зупинок "має бути" в рейсі: беремо найповніший рейс тієї ж лінії й напрямку
ref_len = defaultdict(int)
for tid, g in group.items():
    ref_len[g] = max(ref_len[g], len(known[tid]))

# 3. Повнота кожного рейсу = відомі зупинки / очікувані. Рейс, який проїхав, поки збирач
#    не працював, видно лише на кількох зупинках, тож його повнота низька.
trips = []   # (початок рейсу, повнота)
for tid, stops_times in known.items():
    start = min(stops_times.values())
    complete = min(1.0, len(stops_times) / ref_len[group[tid]])
    trips.append((start, complete))

if not trips:
    raise SystemExit("У файлі немає рейсів.")

# 4. Групуємо за годинами (включно з порожніми між першою й останньою)
buckets = defaultdict(list)
for start, c in trips:
    buckets[start.replace(minute=0, second=0, microsecond=0)].append(c)

first_h, last_h = min(buckets), max(buckets)
hours = []
h = first_h
while h <= last_h:
    hours.append(h)
    h += timedelta(hours=1)

print(f"Рейсів у файлі: {len(trips)}   |   останнє опитування: {last_snapshot:%d.%m %H:%M}")
print(f"Охоплення: {first_h:%d.%m %H:%M} - {last_h:%d.%m %H:%M}\n")
print("Година        рейсів   повнота")

flagged = []
for h in hours:
    cs = buckets.get(h, [])
    in_future = h > last_snapshot
    if not cs:
        note = "  (майбутнє)" if in_future else "  порожньо"
        print(f"{h:%d.%m %H:00}   {0:>6}   {'-' * BAR}{note}")
        if not in_future:
            flagged.append((h, "порожньо"))
        continue
    mean = sum(cs) / len(cs)
    filled = int(round(mean * BAR))
    bar = "█" * filled + "░" * (BAR - filled)
    if in_future:
        note = "  (майбутнє: видно лише частково)"
    elif mean < LOW:
        note = "  <-- ПРОВАЛ"
        flagged.append((h, f"{mean:.0%}"))
    else:
        note = ""
    print(f"{h:%d.%m %H:00}   {len(cs):>6}   {bar} {mean:>4.0%}{note}")

# 5. Підсумок
past = [c for s, c in trips if s <= last_snapshot]
if past:
    good = sum(1 for c in past if c >= 0.8)
    mid = sum(1 for c in past if 0.5 <= c < 0.8)
    bad = sum(1 for c in past if c < 0.5)
    print(f"\nРейси до останнього опитування: {len(past)}")
    print(f"  повні (>=80% зупинок):   {good}  ({good / len(past):.0%})")
    print(f"  часткові (50-80%):       {mid}  ({mid / len(past):.0%})")
    print(f"  майже порожні (<50%):    {bad}  ({bad / len(past):.0%})")

if flagged:
    print("\nПідозрілі проміжки (години підряд об'єднані):")
    spans = []
    for h, info in flagged:
        if spans and h - spans[-1][1] == timedelta(hours=1):
            spans[-1][1] = h
        else:
            spans.append([h, h])
    for a, b in spans:
        end = b + timedelta(hours=1)
        print(f"  {a:%d.%m %H:00} - {end:%H:00}")
    print("Порожні години вночі можуть бути нормальними: тоді транспорт просто не їздить.")
else:
    print("\nПровалів не знайдено.")