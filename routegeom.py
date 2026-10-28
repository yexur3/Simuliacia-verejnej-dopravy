import bisect
import json
import math
import os


class RouteGeometry:
    """Дає форму шляху між двома сусідніми зупинками і точку на ній."""

    def __init__(self, pos, to_screen, paths_file="paths.json"):
        self.pos = pos
        self.to_screen = to_screen
        self.paths = {}
        if os.path.exists(paths_file):
            with open(paths_file, encoding="utf-8") as f:
                self.paths = json.load(f)
        self.cache = {}

    def get(self, a, b):
        """Повертає (точки в пікселях, накопичена довжина) для шляху a -> b."""
        k = (a, b)
        if k in self.cache:
            return self.cache[k]
        lo, hi = (a, b) if a <= b else (b, a)
        raw = self.paths.get(f"{lo}|{hi}")
        if raw:
            pts = [self.to_screen(lon, lat) for lon, lat in raw]
            if a > b:
                pts.reverse()
        else:
            pts = [self.pos[a], self.pos[b]]    # запасний варіант: пряма
        cum = [0.0]
        for p, q in zip(pts, pts[1:]):
            cum.append(cum[-1] + math.dist(p, q))
        self.cache[k] = (pts, cum)
        return pts, cum

    def position(self, a, b, frac):
        """Точка на шляху a -> b, де frac від 0 до 1 це частка пройденого шляху."""
        pts, cum = self.get(a, b)
        total = cum[-1]
        if total == 0:
            return pts[0]
        d = frac * total
        i = bisect.bisect_right(cum, d) - 1
        i = min(max(i, 0), len(pts) - 2)
        seg = cum[i + 1] - cum[i]
        f = (d - cum[i]) / seg if seg > 0 else 0
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        return x1 + (x2 - x1) * f, y1 + (y2 - y1) * f