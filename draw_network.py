import json
import math
from collections import defaultdict

import pygame

WIDTH, HEIGHT, MARGIN = 1000, 800, 40
BG = (20, 22, 28)
COLORS = {"Bus": (90, 160, 255), "Trolleybus": (255, 170, 60)}
DEFAULT_COLOR = (150, 150, 150)

with open("stops.json", encoding="utf-8") as f:
    stops = json.load(f)

stop_by_id = {s["stopId"]: s for s in stops}

# Перетворення координат (те саме, що в draw_stops.py)
lons = [s["position"]["coordinates"][0] for s in stops]
lats = [s["position"]["coordinates"][1] for s in stops]
min_lon, max_lon = min(lons), max(lons)
min_lat, max_lat = min(lats), max(lats)
k = math.cos(math.radians((min_lat + max_lat) / 2))
scale = min((WIDTH - 2 * MARGIN) / ((max_lon - min_lon) * k),
            (HEIGHT - 2 * MARGIN) / (max_lat - min_lat))

def to_screen(lon, lat):
    x = MARGIN + (lon - min_lon) * k * scale
    y = HEIGHT - MARGIN - (lat - min_lat) * scale
    return int(x), int(y)

# Екранна позиція кожної зупинки, порахована один раз
pos = {s["stopId"]: to_screen(*s["position"]["coordinates"]) for s in stops}

# 1. Збираємо рейси: tripId -> [(час, зупинка, тип транспорту), ...]
trips = defaultdict(list)
for s in stops:
    for d in s["departures"]:
        trips[d["tripId"]].append((d["scheduleTime"], s["stopId"], d["vehicleType"]))

# 2. З кожного рейсу беремо пари сусідніх зупинок.
#    set() прибирає дублікати: кілька рейсів однієї лінії дадуть той самий відрізок.
segments = set()
for items in trips.values():
    items.sort()  # час у форматі ISO сортується як звичайний текст
    for a, b in zip(items, items[1:]):
        if a[1] != b[1]:
            segments.add((a[1], b[1], a[2]))

print("Унікальних відрізків:", len(segments))

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Мережа MHD Banská Bystrica")

# 3. Мапа малюється ОДИН раз на окрему поверхню, а далі лише копіюється.
#    Так кожен кадр коштує дуже мало, і потім ми додамо поверх рухомі точки.
background = pygame.Surface((WIDTH, HEIGHT))
background.fill(BG)
for a, b, vtype in segments:
    pygame.draw.line(background, COLORS.get(vtype, DEFAULT_COLOR), pos[a], pos[b], 1)
for p in pos.values():
    pygame.draw.circle(background, (235, 235, 245), p, 2)

clock = pygame.time.Clock()
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    screen.blit(background, (0, 0))
    pygame.display.flip()
    clock.tick(60)

pygame.quit()