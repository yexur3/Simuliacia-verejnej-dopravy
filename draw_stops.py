import json
import math
import pygame

WIDTH, HEIGHT = 1000, 800
MARGIN = 40
BG = (20, 22, 28)
DOT = (230, 230, 240)

with open("stops.json", encoding="utf-8") as f:
    stops = json.load(f)

# Дістаємо координати. Нагадую: у даних порядок [довгота, широта]
lons = [s["position"]["coordinates"][0] for s in stops]
lats = [s["position"]["coordinates"][1] for s in stops]
min_lon, max_lon = min(lons), max(lons)
min_lat, max_lat = min(lats), max(lats)

# На широті 48.7° градус довготи коротший за градус широти
# приблизно в cos(48.7°) ≈ 0.66 раза. Без цієї поправки мапа вийде розтягнутою.
k = math.cos(math.radians((min_lat + max_lat) / 2))

width_deg = (max_lon - min_lon) * k
height_deg = max_lat - min_lat
scale = min((WIDTH - 2 * MARGIN) / width_deg,
            (HEIGHT - 2 * MARGIN) / height_deg)

def to_screen(lon, lat):
    """Перетворює географічні координати на піксельні."""
    x = MARGIN + (lon - min_lon) * k * scale
    # На екрані вісь Y йде вниз, а широта росте вгору, тому віднімаємо
    y = HEIGHT - MARGIN - (lat - min_lat) * scale
    return int(x), int(y)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Zastávky MHD Banská Bystrica")

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill(BG)
    for lon, lat in zip(lons, lats):
        pygame.draw.circle(screen, DOT, to_screen(lon, lat), 3)
    pygame.display.flip()

pygame.quit()