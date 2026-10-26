import json
from collections import Counter
from datetime import datetime, timezone

with open("routes.json", encoding="utf-8") as f:
    routes = json.load(f)

now = datetime.now(timezone.utc)

def parse(s):
    # "2026-09-27T22:00:00.000Z" -> datetime
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def is_valid_now(r):
    start, end = r["validFrom"], r["validTo"]
    # Порожня дата означає «без обмеження» з цього боку
    if start is not None and parse(start) > now:
        return False
    if end is not None and parse(end) < now:
        return False
    return True

valid_now = [r for r in routes if is_valid_now(r)]
no_end = sum(1 for r in routes if r["validTo"] is None)
no_start = sum(1 for r in routes if r["validFrom"] is None)
print("Без дати завершення:", no_end, "| без дати початку:", no_start)
print("Всього ліній:", len(routes))
print("Чинних зараз:", len(valid_now))

print("\nТипи транспорту:", Counter(r["vehicleType"] for r in routes))
print("Агенції:", Counter(r["agency"] for r in routes))

# Які routeId зустрічаються у відправленнях із зупинок?
with open("stops.json", encoding="utf-8") as f:
    stops = json.load(f)

used_ids = {d["routeId"] for s in stops for d in s["departures"]}
known_ids = {r["routeId"] for r in routes}

print("\nroutеId у відправленнях:", len(used_ids))
print("з них є в довіднику ліній:", len(used_ids & known_ids))
print("нема в довіднику:", len(used_ids - known_ids))

valid_ids = {r["routeId"] for r in valid_now}
print("\nЧинні = ті, що в відправленнях?", valid_ids == used_ids)