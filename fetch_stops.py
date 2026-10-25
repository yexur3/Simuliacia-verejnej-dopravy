import json
import requests

URL = "https://opendata.banskabystrica.sk/api/datasets/v1/public-transport/stops/list"

response = requests.post(URL, json={}, timeout=30)
response.raise_for_status()

stops = response.json()

with open("stops.json", "w", encoding="utf-8") as f:
    json.dump(stops, f, ensure_ascii = False, indent = 2)

print("Count of stops:", len(stops))

first = stops[0]
print("First stop:", first["name"])
print("Coordinates:", first["position"]["coordinates"])
print("departures from this stop:", len(first["departures"]))