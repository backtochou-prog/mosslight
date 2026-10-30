"""Natural path composition.

A Path is a Catmull-Rom spline with a width profile, a surface material and
a trampled verge. Stamping paints the verge first (soft, grass showing
through) and then the surface, with a gentle organic wobble on both. Where
two paths meet, `aprons` widens both within a short radius of the junction
so the intersection reads as one worn area, not two overlapping strips.

Decoration (embedded stones, roots, grass patches) is done by the
composition rules, which read `samples()` to know where the path is.
"""
from __future__ import annotations
import math, random
from .terrain_tiles import DIRT, WORN, PEBBLE, EARTH, PAVED
from .terrain_render import catmull_rom
from .noise import fbm

class Path:
    def __init__(self, points, width=0.9, surface=DIRT, verge=WORN, verge_width=1.4, seed=3, wobble=0.6):
        self.points = [tuple(p) for p in points]
        self.widths = [width] * len(points) if not isinstance(width, (list, tuple)) else list(width)
        self.surface, self.verge, self.verge_width = surface, verge, verge_width
        self.seed, self.wobble = seed, wobble
        self._samples = None

    def samples(self, steps=8):
        if self._samples is None:
            pts = catmull_rom(self.points, steps)
            # width per sample by linear interpolation along the control points
            ws = []
            n = len(self.points)
            for i, _ in enumerate(pts):
                t = i / max(1, len(pts) - 1) * (n - 1)
                k = min(n - 2, int(t)); f = t - k
                ws.append(self.widths[k] * (1 - f) + self.widths[k + 1] * f)
            self._samples = list(zip([p[0] for p in pts], [p[1] for p in pts], ws))
        return self._samples

    def width_at(self, i):
        return self._samples[i][2]

    def stamp(self, mm, extra=0.0):
        for (x, y, w) in self.samples():
            vw = w + (self.verge_width - 0.9) + (fbm(x * 3, y * 3, 2.0, self.seed + 1, 2) - 0.5) * 0.9 + extra
            mm.disc(x, y, max(0.4, vw), self.verge, only_if_below=self.verge + 1)
        for (x, y, w) in self.samples():
            sw = w + (fbm(x * 3, y * 3, 2.0, self.seed, 2) - 0.5) * self.wobble + extra
            mm.disc(x, y, max(0.3, sw), self.surface)

    @staticmethod
    def aprons(mm, paths, radius=2.2, widen=0.35):
        """Widen every path near a junction with another path."""
        junctions = []
        for a in range(len(paths)):
            for b in range(a + 1, len(paths)):
                for (x1, y1, _) in paths[a].samples()[::3]:
                    for (x2, y2, _) in paths[b].samples()[::3]:
                        if math.hypot(x1 - x2, y1 - y2) < 0.6:
                            junctions.append(((x1 + x2) / 2, (y1 + y2) / 2))
        # merge nearby junction points
        merged = []
        for j in junctions:
            if all(math.hypot(j[0] - m[0], j[1] - m[1]) > 1.5 for m in merged): merged.append(j)
        for (jx, jy) in merged:
            for p in paths:
                for (x, y, w) in p.samples():
                    d = math.hypot(x - jx, y - jy)
                    if d < radius:
                        f = (1 - d / radius)
                        mm.disc(x, y, w + widen * f + (p.verge_width - 0.9) * 0.6, p.verge, only_if_below=p.verge + 1)
                        mm.disc(x, y, w + widen * f, p.surface)
        return merged

    def nearest(self, x, y):
        """Distance (tiles) from a point to the path centreline, and the local width."""
        best, bw = 1e9, 0
        for (sx, sy, w) in self.samples():
            d = math.hypot(sx - x, sy - y)
            if d < best: best, bw = d, w
        return best, bw

    def curvature_points(self, threshold=0.35):
        """Sample indices where the path bends sharply (used to place embedded stones)."""
        s = self.samples(); out = []
        for i in range(4, len(s) - 4, 4):
            (x0, y0, _), (x1, y1, _), (x2, y2, _) = s[i - 4], s[i], s[i + 4]
            a1 = math.atan2(y1 - y0, x1 - x0); a2 = math.atan2(y2 - y1, x2 - x1)
            d = abs((a2 - a1 + math.pi) % (2 * math.pi) - math.pi)
            if d > threshold: out.append(i)
        return out
