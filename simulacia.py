import bisect
import json
import math
import os
from datetime import datetime
from types import SimpleNamespace as NS

import pygame

from reconstruct import build_trips
from routegeom import RouteGeometry

# ====================== Nastavenia vzhľadu ======================
START_W, START_H = 1280, 900       # počiatočná veľkosť okna (dá sa meniť myšou)
BG = (13, 15, 20)                # nezávisle sivá, ako vo videu

def lift(c, n):
    """Svetlejšia verzia farby (na cesty a pod.)."""
    return tuple(min(255, v + n) for v in c)

ROAD_MINOR = (33, 37, 49)          # drobné ulice
ROAD_MAJOR = (58, 64, 82)          # hlavné cesty
STOP_COLOR = (95, 100, 120)          # hlavné cesty o niečo výraznejšie

TITLE = "Banská Bystrica"
SUBTITLE = "Verejná doprava"
TAGLINE = "každý spoj podľa cestovného poriadku"
HINT1 = "koliesko myši: priblíženie   ťahanie myšou: posun   R: stred mesta   A: celá sieť"
HINT2 = "medzerník: pauza   ↑ ↓: rýchlosť   ← →: ±10 min   F11: celá obrazovka"

# typ dopravy -> (názov v legende, farba)
TYPES = {
    "Bus": ("Autobus", (90, 160, 255)),
    "Trolleybus": ("Trolejbus", (255, 150, 50)),
}
DEFAULT_COLOR = (170, 170, 180)

# štýl čiary linky podľa typu: (hrúbka, jas). Trolejbusy ako "metro" vo videu: hrubé a jasné
LINE_STYLE = {
    "Bus": (1.0, 0.62),
    "Trolleybus": (1.6, 1.0),
}
DEFAULT_LINE_STYLE = (1.1, 0.5)

DOT_RADIUS = 2.6                   # veľkosť bodu vozidla (menšie číslo = menší bod)
DOT_OUTLINE = 1.1                  # hrúbka tmavého obrysu
DOT_WHITENESS = 0.88               # 0 = farba typu, 1 = biely bod (vo videu sú takmer biele)

START_SPEED = 60                   # sekúnd simulácie za 1 reálnu
SS = 2                             # vyhladzovanie pozadia (2 = kresliť 2x väčšie)
HOME_LO, HOME_HI = 0.03, 0.97      # úvodný záber: 3 % - 97 % zastávok (bez vzdialených okrajov)


# ====================== Dáta ======================
with open("stops.json", encoding="utf-8") as f:
    stops = json.load(f)
with open("data/departures.json", encoding="utf-8") as f:
    departures = json.load(f)

stop_ll = {s["stopId"]: tuple(s["position"]["coordinates"]) for s in stops}
lons = [ll[0] for ll in stop_ll.values()]
lats = [ll[1] for ll in stop_ll.values()]
k = math.cos(math.radians(sum(lats) / len(lats)))

# Metrové súradnice len na zostavenie rejsov (nezávisia od zoomu)
pos_m = {sid: (lon * 111320 * k, lat * 110540) for sid, (lon, lat) in stop_ll.items()}
trips, trip_type = build_trips(departures, pos_m)
print("Rejsov pre simuláciu:", len(trips))
trips_times = {tid: [t for t, _ in items] for tid, items in trips.items()}

all_times = [items[0][0] for items in trips.values()] + [items[-1][0] for items in trips.values()]
t_start, t_end = min(all_times), max(all_times)

# Cesty (OpenStreetMap) v "svetových" súradniciach; bbox každej cesty na rýchle vynechanie
roads_w = []
if os.path.exists("roads.json"):
    with open("roads.json", encoding="utf-8") as f:
        for road in json.load(f):
            pts = road["pts"]
            if len(pts) < 2:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            roads_w.append((road["major"], pts, min(xs), max(xs), min(ys), max(ys)))

segments = set()
for tid, items in trips.items():
    for (_, a), (_, b) in zip(items, items[1:]):
        if a != b:
            segments.add((a, b, trip_type[tid]))

def type_key(vtype):
    return vtype if vtype in TYPES else "_default"

def type_color(vtype):
    return TYPES[vtype][1] if vtype in TYPES else DEFAULT_COLOR

def pct(values, p):
    s = sorted(values)
    return s[int(p * (len(s) - 1))]

HOME = (pct(lons, HOME_LO), pct(lons, HOME_HI), pct(lats, HOME_LO), pct(lats, HOME_HI))
ALL = (min(lons), max(lons), min(lats), max(lats))

# ====================== Pohľad (zoom, posun) ======================
view = NS(clon=0.0, clat=0.0, zoom=1.0)
L = NS()                           # rozloženie okna (závisí od veľkosti)
pos = {}                           # zastávka -> pozícia na obrazovke (podľa aktuálneho pohľadu)

def to_screen(lon, lat):
    return (L.cx + (lon - view.clon) * k * view.zoom,
            L.cy - (lat - view.clat) * view.zoom)

def from_screen(x, y):
    return (view.clon + (x - L.cx) / (k * view.zoom),
            view.clat - (y - L.cy) / view.zoom)

def fit_zoom(b):
    lon_lo, lon_hi, lat_lo, lat_hi = b
    w = (lon_hi - lon_lo) * k
    h = lat_hi - lat_lo
    return min((L.W - 2 * L.side) / w, (L.H - L.top - L.bottom) / h)

def fit_view(b):
    view.zoom = fit_zoom(b)
    view.clon = (b[0] + b[1]) / 2
    view.clat = (b[2] + b[3]) / 2

def zoom_limits():
    home, whole = fit_zoom(HOME), fit_zoom(ALL)
    return min(home, whole) * 0.7, home * 16

geo = RouteGeometry(pos, to_screen)

def refresh_positions():
    for sid, (lon, lat) in stop_ll.items():
        pos[sid] = to_screen(lon, lat)
    geo.cache.clear()

def position_at(tid, t):
    trip = trips[tid]
    times = trips_times[tid]
    if t < times[0] or t > times[-1]:
        return None
    i = bisect.bisect_right(times, t) - 1
    i = min(i, len(trip) - 2)
    t1, s1 = trip[i]
    t2, s2 = trip[i + 1]
    frac = (t - t1) / (t2 - t1) if t2 > t1 else 0
    return geo.position(s1, s2, frac)

# ====================== Okno ======================
pygame.init()
pygame.display.set_mode((START_W, START_H), pygame.RESIZABLE)
pygame.display.set_caption("MHD Banská Bystrica – simulácia dopravy")
clock = pygame.time.Clock()
screen = pygame.display.get_surface()

def make_font(size, bold=False):
    return pygame.font.SysFont("segoeui,arial,helvetica,dejavusans", max(8, int(size * L.ui)), bold=bold)

def render(msg, fnt, color):
    return fnt.render(msg, True, color)

def blit_text(img, x, y, anchor="left"):
    r = img.get_rect()
    if anchor == "left":
        r.topleft = (x, y)
    elif anchor == "right":
        r.topright = (x, y)
    else:
        r.midtop = (x, y)
    screen.blit(img, r)

def make_dot(color, r, outline, whiteness=None):
    """Hladký bod (kreslený 4x väčší a zmenšený) s tmavým obrysom."""
    ss = 4
    size = int(math.ceil((r + outline) * 2)) + 2
    big = pygame.Surface((size * ss, size * ss), pygame.SRCALPHA)
    c = (size * ss) // 2
    if outline > 0:
        pygame.draw.circle(big, (6, 7, 10, 235), (c, c), int((r + outline) * ss))
    wh = DOT_WHITENESS if whiteness is None else whiteness
    light = tuple(int(v + (255 - v) * wh) for v in color)
    pygame.draw.circle(big, (*light, 255), (c, c), int(r * ss))
    return pygame.transform.smoothscale(big, (size, size))

def relayout():
    """Prepočíta všetko, čo závisí od veľkosti okna."""
    global screen
    screen = pygame.display.get_surface()
    L.W, L.H = screen.get_size()
    L.ui = min(max(min(L.W / 1200, L.H / 900), 0.7), 2.2)
    ui = L.ui
    L.side, L.top, L.bottom = 60 * ui, 170 * ui, 150 * ui
    L.bar_x0, L.bar_x1, L.bar_y = L.side, L.W - L.side, L.H - 110 * ui
    L.cx, L.cy = L.W / 2, (L.top + L.H - L.bottom) / 2

    L.f_title, L.f_sub, L.f_tag = make_font(46, True), make_font(25), make_font(16)
    L.f_clock, L.f_date = make_font(66, True), make_font(20)
    L.f_small, L.f_hint = make_font(14), make_font(14)

    # Zatemnenie hore a dole, aby bol text čitateľný
    top_h, bot_h = int(L.top), int(L.bottom)
    L.top_fade = pygame.Surface((L.W, top_h), pygame.SRCALPHA)
    for yy in range(top_h):
        pygame.draw.line(L.top_fade, (*BG, int(240 * (1 - yy / top_h) ** 1.4)), (0, yy), (L.W, yy))
    L.bot_fade = pygame.Surface((L.W, bot_h), pygame.SRCALPHA)
    for yy in range(bot_h):
        pygame.draw.line(L.bot_fade, (*BG, int(240 * (yy / bot_h) ** 1.2)), (0, yy), (L.W, yy))

    # Statické texty (vykreslené raz)
    L.static = [
        (render(TITLE, L.f_title, (235, 238, 245)), L.side, 24 * ui, "left"),
        (render(SUBTITLE, L.f_sub, (190, 196, 210)), L.side, 78 * ui, "left"),
        (render(TAGLINE, L.f_tag, (120, 126, 145)), L.side, 112 * ui, "left"),
        (render(HINT1, L.f_hint, (105, 110, 130)), L.W / 2, L.H - 58 * ui, "center"),
        (render(HINT2, L.f_hint, (105, 110, 130)), L.W / 2, L.H - 36 * ui, "center"),
        (render("© OpenStreetMap contributors", L.f_small, (95, 100, 118)), L.W - L.side, L.H - 36 * ui, "right"),
    ]

    # Body vozidiel a legendy
    L.dots = {}
    for key, (_, col) in list(TYPES.items()) + [("_default", ("", DEFAULT_COLOR))]:
        L.dots[key] = make_dot(col, DOT_RADIUS * ui, DOT_OUTLINE * ui)
        L.dots[key + "_legend"] = make_dot(col, 4.0 * ui, 0, 0)

    # Hodiny na časovej osi
    span = (t_end - t_start) / 3600
    L.label_step = 1 if span <= 10 else 2 if span <= 20 else 3
    first = datetime.fromtimestamp(t_start).replace(minute=0, second=0, microsecond=0).timestamp()
    L.ticks = []
    i = 0
    while first + i * 3600 <= t_end:
        tt = first + i * 3600
        if tt >= t_start:
            L.ticks.append((tt, datetime.fromtimestamp(tt).hour))
        i += 1

def x_to_time(x):
    frac = (x - L.bar_x0) / (L.bar_x1 - L.bar_x0)
    return t_start + min(max(frac, 0), 1) * (t_end - t_start)

def time_to_x(t):
    if t_end == t_start:
        return L.bar_x0
    return L.bar_x0 + (t - t_start) / (t_end - t_start) * (L.bar_x1 - L.bar_x0)

# ====================== Pozadie (kreslí sa pri zmene pohľadu) ======================
def build_background():
    W, H, ui = L.W, L.H, L.ui
    big = pygame.Surface((W * SS, H * SS))
    big.fill(BG)

    home_zoom = fit_zoom(HOME)
    zf = view.zoom / home_zoom
    rs = min(max(zf ** 0.35, 0.8), 2.5)          # čiary sa pri priblížení mierne zhrubnú
    kz = k * view.zoom

    # Viditeľný výrez vo "svetových" súradniciach (na vynechanie vzdialených ciest)
    lon_a, lat_a = from_screen(-60, -60)
    lon_b, lat_b = from_screen(W + 60, H + 60)
    lon_lo, lon_hi = min(lon_a, lon_b), max(lon_a, lon_b)
    lat_lo, lat_hi = min(lat_a, lat_b), max(lat_a, lat_b)

    # 1) Cesty (veľmi nenápadné, aby linky vynikli)
    for want_major in (False, True):
        col = ROAD_MAJOR if want_major else ROAD_MINOR
        width = max(1, int(round((1.8 if want_major else 1.0) * ui * rs * SS)))
        for major, pts, x0, x1, y0, y1 in roads_w:
            if major != want_major:
                continue
            if x1 < lon_lo or x0 > lon_hi or y1 < lat_lo or y0 > lat_hi:
                continue
            sp = [((L.cx + (lon - view.clon) * kz) * SS, (L.cy - (lat - view.clat) * view.zoom) * SS)
                  for lon, lat in pts]
            pygame.draw.lines(big, col, False, sp, width)

    # 2) Trasy liniek: najprv tenké (autobusy), nakoniec hrubé (trolejbusy), aby boli navrchu
    def style(vtype):
        return LINE_STYLE.get(vtype, DEFAULT_LINE_STYLE)

    for a, b, vtype in sorted(segments, key=lambda s: style(s[2])[0]):
        w, bright = style(vtype)
        col = tuple(int(c * bright) for c in type_color(vtype))
        pts, _ = geo.get(a, b)
        pygame.draw.lines(big, col, False, [(x * SS, y * SS) for x, y in pts],
                          max(1, int(round(w * ui * rs * SS))))

    # 3) Zastávky (pri priblížení trochu väčšie)
    r = max(1, int(round((1.2 if zf < 2 else 2.2) * ui * SS)))
    for x, y in pos.values():
        pygame.draw.circle(big, STOP_COLOR, (int(x * SS), int(y * SS)), r)

    return pygame.transform.smoothscale(big, (W, H))

def rebuild_view():
    refresh_positions()
    return build_background()

# ====================== Štart ======================
relayout()
fit_view(HOME)
background = rebuild_view()

sim_time = t_start
speed = START_SPEED
paused_speed = START_SPEED
dragging_time = False
drag_map = None                    # (x, y) začiatku ťahania mapy
pan_dx = pan_dy = 0

def apply_pan():
    """Prenesie dočasný posun (v pixeloch) do pohľadu."""
    global pan_dx, pan_dy
    if pan_dx or pan_dy:
        view.clon -= pan_dx / (k * view.zoom)
        view.clat += pan_dy / view.zoom
        pan_dx = pan_dy = 0
        return True
    return False

running = True
while running:
    dt = clock.tick(60) / 1000
    need_rebuild = False
    zoom_steps = 0
    zoom_pos = None

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if abs(my - L.bar_y) <= 18 * L.ui and L.bar_x0 - 12 <= mx <= L.bar_x1 + 12:
                dragging_time = True
                sim_time = x_to_time(mx)
            else:
                drag_map = (mx, my)
        elif event.type == pygame.MOUSEMOTION:
            if dragging_time:
                sim_time = x_to_time(event.pos[0])
            elif drag_map is not None:
                pan_dx = event.pos[0] - drag_map[0]
                pan_dy = event.pos[1] - drag_map[1]
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            dragging_time = False
            if drag_map is not None:
                drag_map = None
                need_rebuild = apply_pan() or need_rebuild
        elif event.type == pygame.MOUSEWHEEL:
            zoom_steps += event.y
            zoom_pos = pygame.mouse.get_pos()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                speed = (speed or paused_speed) * 2
            elif event.key == pygame.K_DOWN:
                speed = max(1, (speed or paused_speed) / 2)
            elif event.key == pygame.K_SPACE:
                if speed:
                    paused_speed, speed = speed, 0
                else:
                    speed = paused_speed
            elif event.key == pygame.K_RIGHT:
                sim_time = min(sim_time + 600, t_end)
            elif event.key == pygame.K_LEFT:
                sim_time = max(sim_time - 600, t_start)
            elif event.key == pygame.K_r:
                pan_dx = pan_dy = 0
                fit_view(HOME)
                need_rebuild = True
            elif event.key == pygame.K_a:
                pan_dx = pan_dy = 0
                fit_view(ALL)
                need_rebuild = True
            elif event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()

    # Zoom (všetky otočenia kolieska v tomto snímku naraz)
    if zoom_steps and zoom_pos:
        apply_pan()
        mx, my = zoom_pos
        lon, lat = from_screen(mx, my)
        zmin, zmax = zoom_limits()
        view.zoom = min(max(view.zoom * (1.25 ** zoom_steps), zmin), zmax)
        view.clon = lon - (mx - L.cx) / (k * view.zoom)
        view.clat = lat + (my - L.cy) / view.zoom
        need_rebuild = True

    # Zmena veľkosti okna (aj F11): prekresliť všetko v natívnom rozlíšení
    if pygame.display.get_surface().get_size() != (L.W, L.H):
        pan_dx = pan_dy = 0
        relayout()
        fit_view(HOME)
        need_rebuild = True

    if need_rebuild:
        background = rebuild_view()

    if not dragging_time:
        sim_time = min(sim_time + dt * speed, t_end)

    # ---------------- Kreslenie ----------------
    screen.fill(BG)
    screen.blit(background, (pan_dx, pan_dy))

    counts = {key: 0 for key in list(TYPES) + ["_default"]}
    for tid in trips:
        p = position_at(tid, sim_time)
        if p is None:
            continue
        key = type_key(trip_type[tid])
        counts[key] += 1
        x, y = p[0] + pan_dx, p[1] + pan_dy
        if -20 <= x <= L.W + 20 and -20 <= y <= L.H + 20:
            dot = L.dots[key]
            screen.blit(dot, (x - dot.get_width() / 2, y - dot.get_height() / 2))
    active = sum(counts.values())

    screen.blit(L.top_fade, (0, 0))
    screen.blit(L.bot_fade, (0, L.H - L.bot_fade.get_height()))
    for img, x, y, anchor in L.static:
        blit_text(img, x, y, anchor)

    # Legenda s počtami
    lx, ly = L.side, 142 * L.ui
    for key, (label, _) in TYPES.items():
        d = L.dots[key + "_legend"]
        screen.blit(d, (lx, ly + 2 * L.ui))
        txt = render(f"{label}  {counts[key]}", L.f_small, (175, 181, 197))
        screen.blit(txt, (lx + d.get_width() + 6 * L.ui, ly))
        lx += d.get_width() + txt.get_width() + 34 * L.ui

    # Veľké hodiny vpravo
    now = datetime.fromtimestamp(sim_time)
    blit_text(render(now.strftime("%H:%M"), L.f_clock, (240, 242, 248)), L.W - L.side, 18 * L.ui, "right")
    blit_text(render(now.strftime("%d.%m.%Y"), L.f_date, (150, 156, 175)), L.W - L.side, 92 * L.ui, "right")
    speed_txt = "pauza" if speed == 0 else f"rýchlosť ×{speed:g}"
    blit_text(render(f"v prevádzke: {active}   ·   {speed_txt}", L.f_small, (120, 126, 145)),
              L.W - L.side, 122 * L.ui, "right")

    # Časová os
    by = L.bar_y
    pygame.draw.line(screen, (55, 60, 78), (L.bar_x0, by), (L.bar_x1, by), max(2, int(3 * L.ui)))
    for n, (tick_t, hour) in enumerate(L.ticks):
        tx = int(time_to_x(tick_t))
        pygame.draw.line(screen, (95, 100, 120), (tx, by - 5 * L.ui), (tx, by + 5 * L.ui), 1)
        if n % L.label_step == 0:
            blit_text(render(f"{hour:02d}:00", L.f_small, (120, 126, 145)), tx, by + 12 * L.ui, "center")
    hx = int(time_to_x(sim_time))
    pygame.draw.line(screen, (90, 160, 255), (L.bar_x0, by), (hx, by), max(2, int(3 * L.ui)))
    pygame.draw.circle(screen, (255, 255, 255), (hx, int(by)), int(6.5 * L.ui))
    blit_text(render(now.strftime("%H:%M"), L.f_small, (225, 230, 240)),
              min(max(hx, L.bar_x0 + 22 * L.ui), L.bar_x1 - 22 * L.ui), by - 34 * L.ui, "center")

    pygame.display.flip()

pygame.quit()