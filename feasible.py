import json
import math
import os


def make_seg_length(stop_ll, paths_file="paths.json"):
    """
    Повертає функцію seg_length(a, b) -> довжина шляху між двома зупинками в метрах:
    по дорозі (paths.json), якщо шлях знайдено, інакше по прямій.
    stop_ll: {stopId: (lon, lat)}.
    """
    lat0 = sum(ll[1] for ll in stop_ll.values()) / len(stop_ll)
    kx, ky = 111320 * math.cos(math.radians(lat0)), 110540
    paths = {}
    if os.path.exists(paths_file):
        with open(paths_file, encoding="utf-8") as f:
            paths = json.load(f)
    cache = {}

    def seg_length(a, b):
        key = (a, b) if a <= b else (b, a)
        if key in cache:
            return cache[key]
        raw = paths.get(f"{key[0]}|{key[1]}")
        if raw:
            pts = [(lon * kx, lat * ky) for lon, lat in raw]
            length = sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))
        else:
            pa, pb = stop_ll[a], stop_ll[b]
            length = math.dist((pa[0] * kx, pa[1] * ky), (pb[0] * kx, pb[1] * ky))
        cache[key] = length
        return length

    return seg_length


def enforce_speed_limit(trips, seg_length, vmax_kmh):
    """
    Жоден відрізок не проїжджається швидше за vmax_kmh. Якщо за розкладом автобус не встигає,
    він прибуває пізніше за час із розкладу, а далі наздоганяє там, де розклад дає запас
    (рейс, який і так їде повільніше за ліміт, не змінюється).
    """
    vmax = vmax_kmh / 3.6
    out = {}
    for tid, items in trips.items():
        cur_t, cur_s = items[0]
        new = [(cur_t, cur_s)]
        for t, s in items[1:]:
            earliest = cur_t + seg_length(cur_s, s) / vmax
            t2 = max(t, earliest)
            new.append((t2, s))
            cur_t, cur_s = t2, s
        out[tid] = new
    return out