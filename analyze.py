import json
from collections import defaultdict

with open("stops.json", encoding = "utf-8") as f:
    stops = json.load(f)

# in what period of time we have departures
all_times = []
for stop in stops:
    for dep in stop["departures"]:
        all_times.append(dep["scheduleTime"])


print("Most early departure:", min(all_times))
print("Most late departure:", max(all_times))
print("All departures:", len(all_times))

# group by lines: tripId -> list (time, stop)
trips = defaultdict(list)
for stop in stops:
    for dep in stop["departures"]:
        trips[dep["tripId"]].append((dep["scheduleTime"], stop["name"]))

print("Unique lines:", len(trips))

multi = {tid: v for tid, v in trips.items() if len(v) >= 2}
print("Lines, that found in more than 2 stops:", len(multi))

example_id = next(iter(multi))
print("\nExample of line", example_id)
for time, name in sorted(multi[example_id]):
    print(" ", time, name)
