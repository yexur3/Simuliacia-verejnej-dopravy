import json
import requests

URL = "https://opendata.banskabystrica.sk/api/datasets/v1/public-transport/routes/list"

r = requests.post(URL, json = {}, timeout = 30)

print("Status:", r.status_code)
r.raise_for_status()
data = r.json()

with open("routes.json", "w", encoding = "utf-8") as f:
    json.dump(data, f, ensure_ascii = False, indent = 2)

print("Type of response:", type(data).__name__)

if isinstance(data, list):
    print("Number of elements:", len(data))
    first = data[0]
else:
    print("Keys of higher level:", list(data.keys()))
    first = data

text = json.dumps(first, ensure_ascii = False, indent = 2)
print(text[:3000])