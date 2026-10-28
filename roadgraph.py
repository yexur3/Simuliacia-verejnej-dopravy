import heapq
import math
from collections import defaultdict

PREC = 6   # знаків після коми в координатах (~0.1 м): збіг = та сама точка


class RoadGraph:
    """Граф доріг: вершини це точки доріг, ребра це відрізки між сусідніми точками."""

    def __init__(self, roads, lat0):
        # Переводимо градуси в метри (приблизно), щоб довжини були реальними
        self.kx = 111320 * math.cos(math.radians(lat0))
        self.ky = 110540
        self.ids = {}        # (lon, lat) -> номер вершини
        self.lonlat = []     # номер -> (lon, lat)
        self.xy = []         # номер -> (x, y) у метрах
        self.adj = []        # номер -> [(сусід, довжина), ...]

        for road in roads:
            prev = None
            for lon, lat in road["pts"]:
                key = (round(lon, PREC), round(lat, PREC))
                nid = self.ids.get(key)
                if nid is None:
                    nid = len(self.lonlat)
                    self.ids[key] = nid
                    self.lonlat.append(key)
                    self.xy.append((key[0] * self.kx, key[1] * self.ky))
                    self.adj.append([])
                if prev is not None and prev != nid:
                    w = math.dist(self.xy[prev], self.xy[nid])
                    self.adj[prev].append((nid, w))
                    self.adj[nid].append((prev, w))
                prev = nid

        # Сітка 100x100 м для швидкого пошуку найближчої вершини
        self.cell = 100.0
        self.grid = defaultdict(list)
        for nid, (x, y) in enumerate(self.xy):
            self.grid[(int(x // self.cell), int(y // self.cell))].append(nid)

    def to_xy(self, lon, lat):
        return lon * self.kx, lat * self.ky

    def nearest(self, lon, lat, max_dist=150):
        """Найближча вершина дороги в межах max_dist метрів, або None."""
        x, y = self.to_xy(lon, lat)
        cx, cy = int(x // self.cell), int(y // self.cell)
        rings = int(max_dist // self.cell) + 1
        best, best_d = None, max_dist
        for dx in range(-rings, rings + 1):
            for dy in range(-rings, rings + 1):
                for nid in self.grid.get((cx + dx, cy + dy), ()):
                    d = math.dist((x, y), self.xy[nid])
                    if d < best_d:
                        best, best_d = nid, d
        return best

    def path(self, src, dst, limit):
        """
        Найкоротший шлях A* від вершини src до dst.
        limit: максимальна довжина шляху в метрах (далі не шукаємо).
        Повертає ([(lon, lat), ...], довжина) або None.
        """
        gx, gy = self.xy[dst]

        def h(n):   # евристика: пряма до цілі
            x, y = self.xy[n]
            return math.hypot(x - gx, y - gy)

        best = {src: 0.0}
        prev = {}
        heap = [(h(src), 0.0, src)]
        while heap:
            f, g, u = heapq.heappop(heap)
            if u == dst:
                out = [u]
                while u in prev:
                    u = prev[u]
                    out.append(u)
                out.reverse()
                return [self.lonlat[n] for n in out], g
            if g > best.get(u, float("inf")):
                continue
            if f > limit:
                return None
            for v, w in self.adj[u]:
                ng = g + w
                if ng < best.get(v, float("inf")):
                    best[v] = ng
                    prev[v] = u
                    heapq.heappush(heap, (ng + h(v), ng, v))
        return None