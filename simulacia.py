import json
import math
import os
from datetime import datetime

import pygame

from reconstruct import build_trips

WIDTH, HEIGHT, MARGIN = 1000, 800, 40
BG = (20, 22, 28)
COLORS = {"Bus": (90, 160, 255), "Trolleybus": (255, 170, 60)}
DEFAULT_COLOR = (150, 150, 150)

with open("stops.json", encoding="utf-8") as f:
    stops = json.load(f)
with open("data/departures.json", encoding="utf-8") as f:
    departures = json.load(f)

# --- Координати ---
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

# --- Рейси ---
trips, trip_type = build_trips(departures, pos)
print("Рейсів для симуляції:", len(trips))

all_times = [items[0][0] for items in trips.values()] + [items[-1][0] for items in trips.values()]
t_start, t_end = min(all_times), max(all_times)

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

# --- Вікно і шрифти ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
font = pygame.font.SysFont("consolas", 20)
small_font = pygame.font.SysFont("consolas", 13)
attribution = small_font.render("© OpenStreetMap contributors", True, (120, 125, 140))
clock = pygame.time.Clock()

# --- Фон: малюється один раз ---
segments = set()
for tid, items in trips.items():
    for (_, a), (_, b) in zip(items, items[1:]):
        if a != b:
            segments.add((a, b, trip_type[tid]))

background = pygame.Surface((WIDTH, HEIGHT))
background.fill(BG)

# 1) Дороги з OpenStreetMap (найнижчий шар)
if os.path.exists("roads.json"):
    with open("roads.json", encoding="utf-8") as f:
        roads = json.load(f)
    # Спершу дрібні, потім головні, щоб головні лежали зверху
    for want_major in (False, True):
        for road in roads:
            if road["major"] != want_major:
                continue
            pts = [to_screen(lon, lat) for lon, lat in road["pts"]]
            if len(pts) < 2:
                continue
            color = (70, 77, 96) if want_major else (45, 50, 64)
            pygame.draw.lines(background, color, False, pts, 2 if want_major else 1)
    print("Доріг намальовано:", len(roads))
else:
    print("roads.json не знайдено, мапа без доріг")

# 2) Лінії маршрутів
for a, b, vtype in segments:
    base = COLORS.get(vtype, DEFAULT_COLOR)
    dim = tuple(int(c * 0.45) for c in base)
    pygame.draw.line(background, dim, pos[a], pos[b], 1)

# 3) Зупинки
for p in pos.values():
    pygame.draw.circle(background, (110, 115, 135), (int(p[0]), int(p[1])), 2)

# --- Основний цикл ---
sim_time = t_start
speed = 60

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
                speed = 0 if speed else 60
            elif event.key == pygame.K_RIGHT:
                sim_time = min(sim_time + 600, t_end)    # +10 хвилин
            elif event.key == pygame.K_LEFT:
                sim_time = max(sim_time - 600, t_start)  # -10 хвилин

    sim_time = min(sim_time + dt * speed, t_end)

    screen.blit(background, (0, 0))
    screen.blit(attribution, (10, HEIGHT - 22))

    active = 0
    for tid, trip in trips.items():
        p = position_at(trip, sim_time)
        if p:
            active += 1
            color = COLORS.get(trip_type[tid], DEFAULT_COLOR)
            pygame.draw.circle(screen, color, (int(p[0]), int(p[1])), 4)

    clock_text = datetime.fromtimestamp(sim_time).strftime("%d.%m %H:%M:%S")
    label = f"{clock_text}   x{speed:g}   на лінії: {active}   (вгору/вниз швидкість, вліво/вправо ±10 хв, пробіл пауза)"
    screen.blit(font.render(label, True, (220, 220, 230)), (15, 12))
    pygame.display.flip()

pygame.quit()