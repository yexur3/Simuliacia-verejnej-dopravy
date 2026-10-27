import json
import math
from collections import defaultdict
from datetime import datetime

import pygame

WIDTH, HEIGHT, MARGIN = 1000, 800, 40
BG = (20, 22, 28)

with open("stops.json", encoding="utf-8") as f:
    stops = json.load(f)
with open("data/departures.json", encoding="utf-8") as f:
    departures = json.load(f)

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
    return x, y

pos = {s["stopId"]: to_screen(*s["position"]["coordinates"]) for s in stops}

def to_seconds(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()

trips = defaultdict(list)
for d in departures.values():
    if d["stopId"] in pos and d["scheduleTime"]:
        trips[d["tripId"]].append((to_seconds(d["scheduleTime"]), d["stopId"]))
for items in trips.values():
    items.sort()

trip_id = max(trips, key=lambda t: len(trips[t]))
trip = trips[trip_id]
print("Рейс", trip_id, "має", len(trip), "зупинок")

def position_at(trip, t):
    if t < trip[0][0] or t > trip[-1][0]:
        return None
    for (t1, s1), (t2, s2) in zip(trip, trip[1:]):
        if t1 <= t <= t2:
            frac = (t - t1) / (t2 - t1) if t2 > t1 else 0
            x1, y1 = pos[s1]
            x2, y2 = pos[s2]
            return x1 + (x2 - x1) * frac, y1 + (y2 - y1) * frac
    return None

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
font = pygame.font.SysFont("consolas", 22)
clock = pygame.time.Clock()

sim_time = trip[0][0] - 60
speed = 30

running = True
while running:
    dt = clock.tick(60) / 1000
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                speed *= 2
            elif event.key == pygame.K_DOWN:
                speed = max(1, speed / 2)
            elif event.key == pygame.K_SPACE:
                speed = 0 if speed else 30

    sim_time += dt * speed

    screen.fill(BG)
    for p in pos.values():
        pygame.draw.circle(screen, (90, 95, 110), (int(p[0]), int(p[1])), 2)
    for _, s in trip:
        pygame.draw.circle(screen, (255, 170, 60), (int(pos[s][0]), int(pos[s][1])), 4)

    bus = position_at(trip, sim_time)
    if bus:
        pygame.draw.circle(screen, (255, 255, 255), (int(bus[0]), int(bus[1])), 7)

    clock_text = datetime.fromtimestamp(sim_time).strftime("%H:%M:%S")
    label = f"{clock_text}   швидкість x{speed:g}   [↑ швидше] [↓ повільніше] [пробіл пауза]"
    screen.blit(font.render(label, True, (220, 220, 230)), (20, 15))
    pygame.display.flip()

pygame.quit()