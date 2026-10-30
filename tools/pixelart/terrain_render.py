"""Material map painting + terrain rendering.

MaterialMap holds three vertex/tile grids:
  m      ground material id per vertex (dual grid)
  snow   snow overlay per vertex (0 none, 1 snow, 2 trampled)
  lush   per-tile lushness (grass mark density family)
  litter per-tile leaf-litter density 0..1 (seasonal overlay)
"""
from __future__ import annotations
import math, random
import numpy as np
from .canvas import Canvas
from .palette import PAL
from .terrain_tiles import (T, MATERIALS, GRASS, WORN, FOREST, SAND, DIRT, EARTH, PEBBLE, MUD, STONE, MOSSY, PAVED,
                            SHALLOW, WATER, SNOW, SNOW_PATH, TerrainTiles, PHASES, mask_code, covers)
from .noise import fbm

BAYER8 = np.array([[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26], [12, 44, 4, 36, 14, 46, 6, 38],
                   [60, 28, 52, 20, 62, 30, 54, 22], [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
                   [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]]) / 64.0

class MaterialMap:
    def __init__(self, w_tiles, h_tiles):
        self.w, self.h = w_tiles, h_tiles
        self.m = np.zeros((h_tiles + 1, w_tiles + 1), dtype=np.int8)
        self.snow = np.zeros((h_tiles + 1, w_tiles + 1), dtype=np.int8)
        self.lush = np.full((h_tiles, w_tiles), 0.5, dtype=np.float32)
        self.litter = np.zeros((h_tiles, w_tiles), dtype=np.float32)

    # -- painting (tile coordinates, floats) --------------------------------
    def _verts(self, x, y, r):
        for vy in range(max(0, int(y - r - 1)), min(self.h + 1, int(y + r + 2))):
            for vx in range(max(0, int(x - r - 1)), min(self.w + 1, int(x + r + 2))):
                if (vx - x) ** 2 + (vy - y) ** 2 <= r * r: yield vx, vy

    def disc(self, x, y, r, mat, only_if_below=None, grid=None):
        g = self.m if grid is None else grid
        for vx, vy in self._verts(x, y, r):
            if only_if_below is None or g[vy, vx] < only_if_below:
                g[vy, vx] = max(g[vy, vx], mat)

    def set_disc(self, x, y, r, mat, grid=None):
        g = self.m if grid is None else grid
        for vx, vy in self._verts(x, y, r): g[vy, vx] = mat

    def metaball(self, balls, mat, threshold=1.0, mode='max', grid=None):
        """Smooth union of discs [(x, y, r)]. mode 'max' respects precedence, 'set' overwrites."""
        g = self.m if grid is None else grid
        for vy in range(self.h + 1):
            for vx in range(self.w + 1):
                s = 0.0
                for (bx, by, br) in balls:
                    d2 = ((vx - bx) ** 2 + (vy - by) ** 2) / (br * br)
                    if d2 < 4: s += (1 - d2 / 4) ** 2 * 2.2
                if s >= threshold:
                    g[vy, vx] = max(g[vy, vx], mat) if mode == 'max' else mat

    def pond(self, balls, deep_threshold=1.9, shore=True):
        """Shallow water from the metaballs; deep water where the field is strong."""
        self.metaball(balls, SHALLOW, 1.0)
        self.metaball(balls, WATER, deep_threshold)
        if shore: self.add_shore()

    def add_shore(self):
        water = self.m >= SHALLOW
        p = np.pad(water, 1)
        near = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
        sel = near & ~water & (self.m < MUD) & (self.m != SAND)
        self.m[sel] = MUD

    def set_lush(self, seed=21):
        for ty in range(self.h):
            for tx in range(self.w):
                self.lush[ty, tx] = fbm(tx, ty, 7.0, seed, 3)

    def litter_disc(self, x, y, r, amount=1.0):
        for ty in range(max(0, int(y - r)), min(self.h, int(y + r + 1))):
            for tx in range(max(0, int(x - r)), min(self.w, int(x + r + 1))):
                d = math.hypot(tx + 0.5 - x, ty + 0.5 - y) / r
                if d < 1: self.litter[ty, tx] = min(1.0, self.litter[ty, tx] + amount * (1 - d))

    def snow_everywhere(self, coverage=1.0, seed=9, shelter=()):
        """Snow over the whole map. Bare ground appears where trees shelter it
        (`shelter` = [(px, py, radius_px)] trunk bases) and, with coverage < 1,
        in a few wind-scoured patches, so a winter scene keeps ground structure."""
        self.snow[:, :] = SNOW
        for vy in range(self.h + 1):
            for vx in range(self.w + 1):
                if self.m[vy, vx] not in (GRASS, WORN, FOREST): continue
                px, py = vx * 16, vy * 16
                sheltered = False
                for (sx, sy, sr) in shelter:
                    d = math.hypot(px - sx, (py - sy + sr * 0.3) * 1.4)
                    if d < sr * (0.75 + 0.35 * fbm(vx, vy, 2.0, seed + 1, 1)):
                        sheltered = True; break
                if sheltered or (coverage < 1.0 and fbm(vx, vy, 6.0, seed, 2) > 0.5 + coverage * 0.5 - 0.18):
                    self.snow[vy, vx] = 0
        self.snow[(self.m == DIRT) | (self.m == EARTH) | (self.m == PEBBLE) | (self.m == PAVED)] = SNOW_PATH
        self.snow[self.m >= SHALLOW] = 0

    def snow_region(self, balls, threshold=1.0):
        # (kept for local tests)
        tmp = np.zeros_like(self.snow)
        self.metaball(balls, 1, threshold, grid=tmp)
        sel = tmp == 1
        path = (self.m == DIRT) | (self.m == EARTH) | (self.m == PEBBLE) | (self.m == PAVED)
        self.snow[sel & ~path & (self.m < SHALLOW)] = SNOW
        self.snow[sel & path] = SNOW_PATH
        # a thin bare ring just at the water's edge
        self.snow[sel & (self.m == MUD)] = 0

    def vertex_mat(self, tx, ty):
        return int(self.m[min(self.h, max(0, int(round(ty)))), min(self.w, max(0, int(round(tx))))])


def catmull_rom(pts, steps):
    out = []
    P = [pts[0]] + list(pts) + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(steps):
            t = s / steps; t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    out.append(tuple(pts[-1]))
    return out


def render_terrain(mm: MaterialMap, tiles: TerrainTiles, rng_seed=5) -> Canvas:
    W, H = mm.w, mm.h
    c = Canvas(W * T, H * T)
    rng = random.Random(rng_seed)
    for ty in range(H):
        for tx in range(W):
            l = mm.lush[ty, tx] + (rng.random() - 0.5) * 0.12
            shade = 'dark' if l < 0.42 else ('sun' if l > 0.60 else 'mid')
            c.blit(tiles.grass[shade][rng.randrange(6)], tx * T, ty * T)
    for layer in range(1, len(MATERIALS)):
        for ty in range(H):
            for tx in range(W):
                corners = (mm.m[ty, tx], mm.m[ty, tx + 1], mm.m[ty + 1, tx], mm.m[ty + 1, tx + 1])
                bits = tuple(int(covers(int(cm), layer)) for cm in corners)
                if not any(bits): continue
                c.blit(tiles.trans[(layer, mask_code(bits), (tx % 2, ty % 2))], tx * T, ty * T)
    return c


def render_snow(c: Canvas, mm: MaterialMap, tiles: TerrainTiles):
    for kind in (SNOW, SNOW_PATH):
        for ty in range(mm.h):
            for tx in range(mm.w):
                corners = (mm.snow[ty, tx], mm.snow[ty, tx + 1], mm.snow[ty + 1, tx], mm.snow[ty + 1, tx + 1])
                if kind == SNOW: bits = tuple(int(cv >= 1) for cv in corners)
                else: bits = tuple(int(cv == SNOW_PATH) for cv in corners)
                if not any(bits): continue
                c.blit(tiles.snow[(kind, mask_code(bits), (tx % 2, ty % 2))], tx * T, ty * T)
    return c


def meadow_tone_pass(c: Canvas, seed=31):
    """Tile-independent density variation on grass: sunlit drifts get extra
    lit tufts, cool dips get shaded pockets. Whole marks, never single dithered
    pixels, so the variation reads as grass growing unevenly."""
    g = PAL.ramp('grass')
    base = c.a == g[3]
    rng = random.Random(seed)
    H, W = c.a.shape
    for ty in range(0, H, 8):
        for tx in range(0, W, 8):
            v = fbm(tx, ty, 52.0, seed, 3)
            if v > 0.57:
                n = int((v - 0.57) * 9 + rng.random())
                for _ in range(n):
                    x, y = tx + rng.randrange(8), ty + rng.randrange(8)
                    pts = ((x, y - 1), (x + 2, y - 1), (x + 1, y), (x + 1, y - 2))
                    if all(0 <= px < W and 0 <= py < H and base[py, px] for px, py in pts):
                        for px, py in pts: c.a[py, px] = g[4]
                        if y + 1 < H and base[y + 1, x + 1]: c.a[y + 1, x + 1] = g[2]
                # a tiny wildflower now and then in the sunniest drifts
                if v > 0.66 and rng.random() < 0.22:
                    x, y = tx + rng.randrange(8), ty + rng.randrange(1, 8)
                    if x + 1 < W and base[y, x] and base[y - 1, x] and base[y, x + 1]:
                        c.a[y - 1, x] = PAL.i('flower_w', 2) if rng.random() < 0.6 else PAL.i('flower_y', 1)
                        c.a[y, x] = g[2]
            elif v < 0.41:
                n = int((0.41 - v) * 8 + rng.random())
                for _ in range(n):
                    x, y = tx + rng.randrange(8), ty + rng.randrange(8)
                    if x + 1 < W and base[y, x] and base[y, x + 1]:
                        c.a[y, x] = g[2]; c.a[y, x + 1] = g[2]
    return c


def water_depth_pass(c: Canvas, rng_seed=9):
    """Deep water: a few glints on the dark surface; shallow water: crisp
    highlight dashes (2-5 px, light with pale ends) as still-water sparkle."""
    wr = PAL.ramp('water')
    rng = random.Random(rng_seed)
    ys, xs = np.nonzero(c.a == wr[3])
    for _ in range(len(xs) // 110):
        k = rng.randrange(len(xs)); x, y = int(xs[k]), int(ys[k])
        L = rng.randint(2, 5)
        if all(c.get(x + i, y) == wr[3] for i in range(L)):
            for i in range(L): c.put(x + i, y, wr[5] if 0 < i < L - 1 else wr[4])
    ys, xs = np.nonzero(c.a == wr[1])
    for _ in range(len(xs) // 140):
        k = rng.randrange(len(xs)); x, y = int(xs[k]), int(ys[k])
        L = rng.randint(2, 4)
        for i in range(L):
            if c.get(x + i, y) == wr[1]: c.put(x + i, y, wr[2] if i in (0, L - 1) else wr[3])
    return c


def ice_pass(c: Canvas, seed=17):
    """Winter: frozen water gets a pale rim where it meets the bank, a second
    paler ring, and a few hairline cracks on the open ice."""
    wr = PAL.ramp('water'); ice = PAL.ramp('ice')
    water = np.isin(c.a, wr)
    p = np.pad(water, 1)
    inner = water & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    rim1 = water & ~inner
    q = np.pad(inner, 1)
    inner2 = inner & q[:-2, 1:-1] & q[2:, 1:-1] & q[1:-1, :-2] & q[1:-1, 2:]
    rim2 = inner & ~inner2
    c.a[rim1] = ice[4]
    idx = np.indices(c.a.shape)
    c.a[rim2 & ((idx[0] + idx[1]) % 2 == 0)] = ice[3]
    rng = random.Random(seed)
    ys, xs = np.nonzero(inner2)
    for _ in range(len(xs) // 90):
        k = rng.randrange(len(xs)); x, y = int(xs[k]), int(ys[k])
        dx, dy = rng.choice(((1, 0), (1, 1), (1, -1)))
        for s in range(rng.randint(4, 9)):
            if inner2[min(c.h - 1, max(0, y)), min(c.w - 1, max(0, x))]: c.put(x, y, ice[1])
            x += dx; y += dy if s % 2 else 0
    return c


def litter_pass(c: Canvas, mm: MaterialMap, season='spring', seed=41):
    """Leaf litter overlay on grass/forest/worn: clustered leaves, density per
    tile from mm.litter scaled by season."""
    scale = {'spring': 0.6, 'summer': 0.3, 'autumn': 1.8, 'winter': 0.0}[season]
    if scale == 0: return c
    rng = random.Random(seed)
    ok = np.isin(c.a, PAL.ramp('grass') + PAL.ramp('forest') + PAL.ramp('worn'))
    ll = PAL.ramp('leaf_litter')
    for ty in range(mm.h):
        for tx in range(mm.w):
            d = mm.litter[ty, tx] * scale
            if d <= 0.02: continue
            n = int(d * 2.5 + rng.random())
            for _ in range(n):                               # a drift of 2-4 leaves
                x, y = tx * T + rng.randrange(T), ty * T + rng.randrange(T)
                for _k in range(rng.randint(2, 4)):
                    if 0 <= x < c.w - 2 and 0 <= y < c.h and ok[y, x] and ok[y, x + 1]:
                        col = ll[rng.choice((1, 2, 2, 3))]
                        c.put(x, y, col); c.put(x + 1, y, ll[rng.choice((1, 2))])
                        if rng.random() < 0.5 and y > 0 and ok[y - 1, x + 1]: c.put(x + 1, y - 1, col)
                    x += rng.choice((-3, 2, 3)); y += rng.choice((-1, 0, 1, 2))
    return c
