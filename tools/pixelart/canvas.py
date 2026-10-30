"""Indexed pixel canvas + drawing primitives for authoring pixel art.

A Canvas is an (h, w) uint8 numpy array of palette indices (0 = transparent).
All primitives are integer/pixel based so shapes stay crisp.
"""
from __future__ import annotations
import math
import random
import numpy as np
from PIL import Image
from .palette import PAL

class Canvas:
    def __init__(self, w: int, h: int, fill: int = 0):
        self.w, self.h = w, h
        self.a = np.full((h, w), fill, dtype=np.uint8)

    # -- basic access -------------------------------------------------------
    def inb(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def put(self, x, y, idx):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = idx

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return int(self.a[y, x])
        return 0

    def mask(self):
        return self.a != 0

    def copy(self):
        c = Canvas(self.w, self.h)
        c.a = self.a.copy()
        return c

    # -- primitives -----------------------------------------------------------
    def rect(self, x, y, w, h, idx):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 > x0 and y1 > y0:
            self.a[y0:y1, x0:x1] = idx

    def hline(self, x0, x1, y, idx):
        if x1 < x0: x0, x1 = x1, x0
        self.rect(x0, y, x1 - x0 + 1, 1, idx)

    def vline(self, x, y0, y1, idx):
        if y1 < y0: y0, y1 = y1, y0
        self.rect(x, y0, 1, y1 - y0 + 1, idx)

    def line(self, x0, y0, x1, y1, idx):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.put(x0, y0, idx)
            if x0 == x1 and y0 == y1: break
            e2 = 2 * err
            if e2 >= dy: err += dy; x0 += sx
            if e2 <= dx: err += dx; y0 += sy

    def ellipse(self, cx, cy, rx, ry, idx):
        """Filled ellipse centred at (cx, cy) (float ok). Pixel centres inside."""
        if rx <= 0 or ry <= 0: return
        x0, x1 = int(math.floor(cx - rx)), int(math.ceil(cx + rx))
        y0, y1 = int(math.floor(cy - ry)), int(math.ceil(cy + ry))
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            dy = (y + 0.5 - cy) / ry
            if abs(dy) > 1: continue
            half = rx * math.sqrt(max(0.0, 1 - dy * dy))
            xa = int(math.ceil(cx - half - 0.5))
            xb = int(math.floor(cx + half - 0.5))
            if xb >= xa and xb >= 0 and xa < self.w:
                self.a[y, max(0, xa):min(self.w, xb + 1)] = idx

    def ellipse_mask(self, cx, cy, rx, ry):
        m = Canvas(self.w, self.h)
        m.ellipse(cx, cy, rx, ry, 1)
        return m.a == 1

    def poly(self, pts, idx):
        """Filled polygon, scanline, pts list of (x,y) float."""
        ys = [p[1] for p in pts]
        y0, y1 = int(math.floor(min(ys))), int(math.ceil(max(ys)))
        n = len(pts)
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            yc = y + 0.5
            xs = []
            for k in range(n):
                (xa, ya), (xb, yb) = pts[k], pts[(k + 1) % n]
                if (ya <= yc < yb) or (yb <= yc < ya):
                    xs.append(xa + (yc - ya) * (xb - xa) / (yb - ya))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                a_, b_ = int(math.ceil(xs[k] - 0.5)), int(math.floor(xs[k + 1] - 0.5))
                if b_ >= a_ and b_ >= 0 and a_ < self.w:
                    self.a[y, max(0, a_):min(self.w, b_ + 1)] = idx

    def paint_mask(self, m, idx):
        self.a[m] = idx

    def blit(self, src: 'Canvas', x: int, y: int, flip=False):
        s = src.a[:, ::-1] if flip else src.a
        sh, sw = s.shape
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + sw), min(self.h, y + sh)
        if x1 <= x0 or y1 <= y0: return
        sub = s[y0 - y:y1 - y, x0 - x:x1 - x]
        dst = self.a[y0:y1, x0:x1]
        dst[sub != 0] = sub[sub != 0]

    def blit_masked(self, src: 'Canvas', x: int, y: int, allow: np.ndarray):
        """Blit only where `allow` (full-canvas bool mask) is true."""
        sh, sw = src.a.shape
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + sw), min(self.h, y + sh)
        if x1 <= x0 or y1 <= y0: return
        sub = src.a[y0 - y:y1 - y, x0 - x:x1 - x]
        dst = self.a[y0:y1, x0:x1]
        al = allow[y0:y1, x0:x1]
        sel = (sub != 0) & al
        dst[sel] = sub[sel]

    # -- pixel-art finishing ----------------------------------------------------
    def outline_inside(self, idx, mask=None):
        """Replace silhouette-boundary pixels (those touching transparency,
        4-neighbourhood) with `idx`. Gives the classic selective dark outline
        without growing the sprite."""
        m = self.mask() if mask is None else mask
        p = np.pad(m, 1)
        inner = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
        edge = m & ~inner
        self.a[edge] = idx

    def outline_outside(self, idx, mask=None):
        m = self.mask() if mask is None else mask
        p = np.pad(m, 1)
        grown = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
        self.a[grown & ~m] = idx

    def shade_mask(self, m, deep=False):
        """Darken existing pixels under mask by one rank (cast shadows)."""
        table = np.array(PAL.shade2 if deep else PAL.shade, dtype=np.uint8)
        sel = m & (self.a != 0)
        self.a[sel] = table[self.a[sel]]

    def remap(self, m, table):
        t = np.array(table, dtype=np.uint8)
        self.a[m] = t[self.a[m]]

    def scatter(self, rng: random.Random, region: np.ndarray, count: int, idx, clump=0):
        """Place `count` pixels inside region mask; clump>0 adds that many
        adjacent pixels per seed so detail reads as tufts, not noise."""
        ys, xs = np.nonzero(region)
        if len(xs) == 0: return
        for _ in range(count):
            k = rng.randrange(len(xs))
            x, y = int(xs[k]), int(ys[k])
            self.put(x, y, idx)
            for _c in range(clump):
                x += rng.choice((-1, 0, 1)); y += rng.choice((-1, 0, 0))
                if region[min(self.h-1,max(0,y)), min(self.w-1,max(0,x))]:
                    self.put(x, y, idx)

    # -- export -------------------------------------------------------------
    def to_rgba(self, lut: list[tuple[int, int, int]]) -> np.ndarray:
        lut_a = np.array(lut, dtype=np.uint8)
        rgb = lut_a[self.a]
        alpha = (self.a != 0).astype(np.uint8) * 255
        return np.dstack([rgb, alpha])

    def save(self, path, lut=None, scale=1):
        lut = lut or PAL.day
        img = Image.fromarray(self.to_rgba(lut), 'RGBA')
        if scale != 1:
            img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
        img.save(path)
        return img


def shaded_blob(c: Canvas, cx, cy, rx, ry, ramp, light=(-0.35, -0.35), rng=None, texture=0.0,
                ranks=(1, 2, 3, 4), outline_rank=None):
    """Draw a shaded ellipsoid clump: shadow / mid / light / highlight bands
    offset toward the light vector. Used for canopies, shrubs, boulders."""
    sh, mid, lt, hi = [ramp[min(len(ramp)-1, r)] for r in ranks]
    c.ellipse(cx, cy, rx, ry, sh)
    ox, oy = light[0] * rx * 0.5, light[1] * ry * 0.5
    c.ellipse(cx + ox * 0.6, cy + oy * 0.6, rx * 0.86, ry * 0.86, mid)
    c.ellipse(cx + ox * 1.1, cy + oy * 1.1, rx * 0.58, ry * 0.58, lt)
    c.ellipse(cx + ox * 1.5, cy + oy * 1.5, rx * 0.28, ry * 0.28, hi)
    if rng and texture > 0:
        # leafy texture: speckle light pixels into mid band & dark into shadow band
        m = c.ellipse_mask(cx + ox * 0.6, cy + oy * 0.6, rx * 0.86, ry * 0.86)
        c.scatter(rng, m, int(rx * ry * texture), lt, clump=1)
        s = c.ellipse_mask(cx, cy, rx, ry) & ~m
        c.scatter(rng, s, int(rx * ry * texture * 0.5), mid, clump=1)
