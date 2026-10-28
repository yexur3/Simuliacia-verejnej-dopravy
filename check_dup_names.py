import json
from collections import defaultdict

with open("stops.json", encoding="utf-8") as f:
    stops = json.load(f)

by_name = defaultdict(list)
for s in stops:
    by_name[s["name"]].append(s["stopId"])

dups = {n: ids for n, ids in by_name.items() if len(ids) > 1}
print("Назв, що мають кілька stopId:", len(dups), "із", len(by_name))
for n in ("Námestie slobody", "Úsvit", "Kyjevské námestie"):
    print(n, "->", by_name.get(n))