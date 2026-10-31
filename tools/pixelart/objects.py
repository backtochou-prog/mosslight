"""Original object sprites for MOSSlight, authored as indexed pixel art.

Conventions (see ART_BIBLE.md):
  * 3/4 top-down view. Light from the upper-left; cast shadows fall down-right.
  * Selective outline: darkest ramp colour on the outer silhouette only.
  * Every sprite declares its ground-contact origin (ox, oy) and a ground
    shadow ellipse so placement, y-sorting and ground contact are consistent.
"""
from __future__ import annotations
import math, random
from dataclasses import dataclass, field
import numpy as np
from .canvas import Canvas, shaded_blob
from .palette import PAL

@dataclass
class Sprite:
    name: str
    c: Canvas
    ox: int                      # origin (ground contact) inside the sprite
    oy: int
    shadow: tuple | None = None  # (rx, ry, dx, dy) relative to origin, None = no shadow
    soft_shadow: bool = False    # dither the outer ring of the shadow
    tags: tuple = ()

    @property
    def w(self): return self.c.w
    @property
    def h(self): return self.c.h

def R(fam): return PAL.ramp(fam)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _outline(c: Canvas, idx):
    c.outline_inside(idx)

def _mask_of(c: Canvas, fams):
    return np.isin(c.a, sum([R(f) for f in fams], []))

def _speckle_in(c, rng, m, n, idx, clump=1):
    c.scatter(rng, m, n, idx, clump)

def sun_tips(c: Canvas, rng, m, n, idx):
    """Single bright pixels on the upper-left of lit areas."""
    ys, xs = np.nonzero(m)
    if not len(xs): return
    order = np.argsort(xs * 0.7 + ys)   # upper-left first
    for k in order[:max(1, len(xs) // 6)]:
        if rng.random() < n / max(1, len(xs) // 6):
            c.put(int(xs[k]), int(ys[k]), idx)

# ---------------------------------------------------------------------------
# trees
# ---------------------------------------------------------------------------
def trunk(c, x, y_top, y_base, w, ramp, roots=True, knots=True, rng=None):
    """Cylindrical trunk: lit left band, mid, dark right band; root flare at base."""
    sh, dk, mid, lt = ramp[0], ramp[1], ramp[2], ramp[3]
    half = w // 2
    for y in range(y_top, y_base + 1):
        flare = 0
        if roots and y > y_base - 4:
            flare = (y - (y_base - 4))
        x0, x1 = x - half - flare, x + half + flare
        c.hline(x0, x1, y, mid)
        c.hline(x0, x0 + max(1, w // 4), y, lt)
        c.hline(x1 - max(1, w // 3), x1, y, dk)
        c.put(x1, y, sh)
    if roots:
        # separate root toes
        c.hline(x - half - 4, x - half - 2, y_base, dk)
        c.hline(x + half + 2, x + half + 4, y_base, sh)
        c.put(x - half - 3, y_base - 1, mid)
    if knots and rng:
        ky = rng.randint(y_top + 3, y_base - 6)
        c.put(x + 1, ky, sh); c.put(x, ky, dk); c.put(x + 1, ky + 1, dk)
    # bark lines
    if rng:
        for _ in range(3):
            yy = rng.randint(y_top + 2, y_base - 5)
            c.vline(x - 1 + rng.randint(0, 1), yy, yy + rng.randint(2, 4), dk)

def leaf_arcs(c, rng, region, n, idx, down=False):
    """Tiny 3-px arcs (leaf bunches) scattered in a region."""
    ys, xs = np.nonzero(region)
    if not len(xs): return
    for _ in range(n):
        k = rng.randrange(len(xs)); x, y = int(xs[k]), int(ys[k])
        pts = ((x, y), (x + 1, y + (1 if down else -1)), (x + 2, y))
        if all(0 <= py < region.shape[0] and 0 <= px < region.shape[1] and region[py, px] for px, py in pts):
            for px, py in pts: c.put(px, py, idx)

def leaf_notches(c, m, rng, rate=0.14):
    """Bite small 2-px notches out of the silhouette so the outline reads as
    leaves, not a balloon. Applied before the caller's outline pass."""
    p = np.pad(m, 1)
    top = m & ~p[:-2, 1:-1]; left = m & ~p[1:-1, :-2]; right = m & ~p[1:-1, 2:]
    ys, xs = np.nonzero(top | left | right)
    order = list(range(len(xs))); rng.shuffle(order)
    taken = set()
    for k in order:
        x, y = int(xs[k]), int(ys[k])
        if rng.random() > rate or (x // 3, y // 3) in taken: continue
        taken.add((x // 3, y // 3))
        c.put(x, y, 0)
        if top[y, x] and x + 1 < c.w and m[y, x + 1]: c.put(x + 1, y, 0)
        elif y + 1 < c.h and m[y + 1, x]: c.put(x, y + 1, 0)

def leaf_tips(c, rng, region, n, idx):
    """Small '^' leaf-tip marks: the sparkle on the lit side of a leaf mass."""
    ys, xs = np.nonzero(region)
    if not len(xs): return
    for _ in range(n):
        k = rng.randrange(len(xs)); x, y = int(xs[k]), int(ys[k])
        pts = ((x, y - 1), (x - 1, y), (x + 1, y))
        if all(0 <= py < region.shape[0] and 0 <= px < region.shape[1] and region[py, px] for px, py in pts):
            for px, py in pts: c.put(px, py, idx)

def canopy_clusters(c, lobes, ramp, rng, light=(-0.4, -0.45)):
    """Foliage as overlapping leaf masses, drawn back to front.

    Each mass: a mid body, a crisp lit cap on its upper-left, a highlight
    inside the cap, a shaded crescent on its lower-right, and a **dark
    separation rim** where its lower edge sits over the mass behind it. The
    mass behind gets a 2-px shade band under the new one. Then leaf-tip
    marks in the caps, dark 'v' marks in the shade, and a notched
    silhouette. Crisp bands, no dither: the masses must read at 1x."""
    fam = PAL.family_of(ramp[0])
    hi2 = ramp[5] if len(ramp) > 5 else ramp[4]
    def canopy_mask(): return _mask_of(c, [fam])
    idx = np.indices(c.a.shape)
    ymin = min(cy - ry for (_, cy, _, ry) in lobes); ymax = max(cy + ry for (_, cy, _, ry) in lobes)
    for (cx, cy, rx, ry) in lobes:
        # light from above: masses low in the crown sit one rank deeper in shade
        h = (cy - ymin) / max(1, ymax - ymin)
        sh = 1 if h > 0.62 else 0
        R = [ramp[max(0, k - sh)] for k in range(len(ramp))]
        prev = canopy_mask()
        E = c.ellipse_mask(cx, cy, rx, ry)
        # shade band on the canopy behind, just under this mass
        band = c.ellipse_mask(cx + 1, cy + 2, rx + 1.5, ry + 1.5) & prev & ~E & (idx[0] > cy)
        c.a[band] = R[1]
        c.a[E] = R[2]
        cap = c.ellipse_mask(cx + light[0] * rx * 0.28, cy + light[1] * ry * 0.34, rx * 0.80, ry * 0.76) & E
        c.a[cap] = R[3]
        hi = c.ellipse_mask(cx + light[0] * rx * 0.55, cy + light[1] * ry * 0.62, rx * 0.44, ry * 0.40) & E
        c.a[hi] = R[4]
        cres = E & ~c.ellipse_mask(cx + light[0] * rx * 0.22, cy + light[1] * ry * 0.26, rx * 0.96, ry * 0.92)
        c.a[cres] = R[1]
        # dark separation rim: this mass's lower edge over previously drawn canopy
        p = np.pad(E, 1)
        rim = E & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
        pv = np.pad(prev, 1)
        touch = rim & (pv[2:, 1:-1] | pv[1:-1, 2:] | pv[2:, 2:] | pv[2:, :-2]) & (idx[0] > cy - ry * 0.15)
        c.a[touch] = ramp[0]
        # scallops: bumps on the lit rim, notches on the shade rim
        for k in range(int(rx * 0.55)):
            ang = rng.uniform(-math.pi * 0.95, -math.pi * 0.1)
            bx, by = cx + math.cos(ang) * rx, cy + math.sin(ang) * ry
            c.ellipse(bx, by, 1.6, 1.3, R[3] if ang < -math.pi * 0.4 else R[2])
    m = canopy_mask()
    area = int(m.sum())
    leaf_tips(c, rng, c.a == ramp[3], area // 55, ramp[4])
    leaf_tips(c, rng, c.a == ramp[4], area // 70, hi2)
    # sunlit crest: the top rows of the crown catch the brightest rank
    ys, xs = np.nonzero(m); top = ys.min() if len(ys) else 0
    crest = m & (idx[0] <= top + 3) & np.isin(c.a, [ramp[3], ramp[4]])
    c.a[crest] = hi2
    leaf_arcs(c, rng, c.a == ramp[2], area // 90, ramp[1], down=True)
    leaf_arcs(c, rng, c.a == ramp[1], area // 110, ramp[0], down=True)
    leaf_notches(c, m, rng)
    return canopy_mask()

def canopy_clumps(c, clumps, ramp, rng, texture=0.05, light=(-0.35, -0.4)):
    return canopy_clusters(c, clumps, ramp, rng, light)

def tree_oak(variant=0) -> Sprite:
    rng = random.Random(100 + variant)
    W, H = 72, 80
    c = Canvas(W, H)
    base_y = H - 4
    tx = W // 2 + rng.randint(-2, 2)
    oak = R('oak'); wood = R('wood')
    trunk(c, tx, 44, base_y, 10 + rng.randint(0, 2), wood, rng=rng)
    _outline(c, wood[0])
    cx, cy = tx, 30
    # four silhouettes: broad / tall-crowned / leaning / wide-and-flat
    layouts = [
        [(cx - 4, cy + 12, 16, 8), (cx + 14, cy + 10, 14, 8), (cx - 20, cy + 6, 13, 9), (cx + 18, cy - 2, 13, 9),
         (cx - 2, cy + 2, 22, 13), (cx - 14, cy - 8, 13, 9), (cx + 8, cy - 10, 14, 9), (cx - 3, cy - 15, 11, 7)],
        [(cx - 10, cy + 12, 15, 8), (cx + 12, cy + 12, 14, 8), (cx - 20, cy + 2, 12, 9), (cx + 19, cy + 2, 12, 9),
         (cx, cy + 2, 20, 13), (cx - 9, cy - 10, 13, 9), (cx + 9, cy - 11, 13, 9), (cx + 1, cy - 20, 10, 7), (cx - 4, cy - 24, 7, 5)],
        [(cx - 2, cy + 12, 17, 8), (cx + 16, cy + 8, 13, 8), (cx - 22, cy + 4, 12, 9), (cx + 4, cy + 1, 22, 13),
         (cx - 14, cy - 7, 13, 9), (cx + 14, cy - 9, 13, 9), (cx + 2, cy - 15, 12, 7), (cx - 8, cy - 18, 8, 5)],
        [(cx - 8, cy + 13, 16, 7), (cx + 10, cy + 13, 16, 7), (cx - 24, cy + 6, 12, 8), (cx + 24, cy + 6, 12, 8),
         (cx, cy + 3, 24, 12), (cx - 12, cy - 7, 14, 8), (cx + 12, cy - 7, 14, 8), (cx, cy - 13, 13, 7)],
    ][variant % 4]
    canopy_clusters(c, layouts, oak, rng)
    m = _mask_of(c, ['oak'])
    # deep underside where the canopy overhangs the trunk
    under = c.ellipse_mask(cx + 2, cy + 18, 17, 4) & m
    c.a[under] = oak[0]
    sun_tips(c, rng, (c.a == oak[4]), 8, oak[6])
    c.outline_inside(oak[0], mask=m)
    for i in range(3):                          # leaves hanging over the trunk
        c.put(tx - 4 + i * 3, cy + 21 + (i % 2), oak[1])
    return Sprite(f'oak_{variant}', c, tx, base_y, shadow=(28, 6, 9, -1), soft_shadow=True, tags=('tree', 'ysort'))

def tree_birch(variant=0) -> Sprite:
    rng = random.Random(200 + variant)
    W, H = 44, 84
    c = Canvas(W, H)
    base_y = H - 3
    tx = W // 2
    b = R('birch'); bark = R('bark_birch')
    for y in range(44, base_y + 1):
        fl = 1 if y > base_y - 3 else 0
        c.hline(tx - 2 - fl, tx + 2 + fl, y, bark[2])
        c.put(tx - 2 - fl, y, bark[3])
        c.hline(tx + 1, tx + 2 + fl, y, bark[1])
    for _ in range(6):
        yy = rng.randint(46, base_y - 4); xx = tx - 2 + rng.randint(0, 2)
        c.hline(xx, xx + rng.randint(1, 2), yy, bark[0])
    c.outline_inside(bark[0])
    cx, cy = tx + rng.randint(-1, 1), 26
    lobes = [[(cx - 6, cy + 14, 11, 6), (cx + 9, cy + 12, 10, 6), (cx - 13, cy + 4, 9, 8), (cx + 13, cy + 3, 9, 8),
              (cx, cy + 2, 15, 11), (cx - 7, cy - 9, 10, 8), (cx + 7, cy - 10, 10, 8), (cx, cy - 18, 8, 6)],
             [(cx - 8, cy + 13, 11, 6), (cx + 8, cy + 14, 10, 6), (cx - 14, cy + 2, 9, 8), (cx + 12, cy + 5, 9, 7),
              (cx + 1, cy + 1, 15, 11), (cx - 5, cy - 10, 11, 8), (cx + 9, cy - 8, 9, 7), (cx - 2, cy - 19, 8, 6), (cx + 3, cy - 24, 5, 4)]][variant % 2]
    canopy_clusters(c, lobes, b, rng, light=(-0.4, -0.5))
    m = _mask_of(c, ['birch'])
    for _ in range(5):                          # airy: a few gaps
        hx, hy = cx + rng.randint(-9, 9), cy + rng.randint(-6, 8)
        if 0 <= hy < H and 0 <= hx < W and m[hy, hx] and c.a[hy, hx] in (b[2], b[3]):
            c.put(hx, hy, b[0]); c.put(hx + 1, hy, b[0])
    under = c.ellipse_mask(cx, cy + 18, 10, 3) & m
    c.a[under] = b[0]
    sun_tips(c, rng, (c.a == b[4]), 6, b[5])
    c.outline_inside(b[0], mask=m)
    return Sprite(f'birch_{variant}', c, tx, base_y, shadow=(16, 4, 6, -1), soft_shadow=True, tags=('tree', 'ysort'))

def tree_pine(variant=0) -> Sprite:
    rng = random.Random(300 + variant)
    W, H = 44, 96
    c = Canvas(W, H)
    base_y = H - 3
    tx = W // 2
    p = R('pine'); wood = R('wood')
    trunk(c, tx, 60, base_y, 6, wood, roots=True, knots=False, rng=rng)
    c.outline_inside(wood[0])
    # tiers: (cy, half_w, h) from bottom to top, each an upward triangle with a
    # scalloped bottom edge
    tiers = [(70, 20, 16), (56, 16, 14), (43, 12, 12), (31, 8, 10), (21, 4, 8)]
    for i, (cy, hw, th) in enumerate(tiers):
        jitter = rng.randint(-1, 1)
        pts = [(tx + jitter, cy - th), (tx + hw, cy), (tx - hw, cy)]
        c.poly(pts, p[2])
        # scallops along the bottom edge
        for k in range(-hw, hw, 4):
            c.ellipse(tx + k + 2, cy, 2.5, 2, p[2])
        # shading: lit left half, dark right third, dark underside
        tri_left = Canvas(W, H); tri_left.poly([(tx + jitter, cy - th), (tx + jitter, cy), (tx - hw, cy)], 1)
        tri_right = Canvas(W, H); tri_right.poly([(tx + jitter, cy - th), (tx + hw, cy), (tx + hw * 0.5, cy)], 1)
        m_tier = (c.a == p[2])
        c.a[(tri_left.a == 1) & m_tier] = p[3]
        c.a[(tri_right.a == 1) & m_tier] = p[1]
        # highlight ridge on the upper-left edge
        for s in range(0, th, 2):
            x = int(tx + jitter - (hw * s / th)); y = cy - th + s
            if c.get(x + 1, y) in (p[2], p[3]): c.put(x + 1, y, p[4])
        # underside shadow band
        m_all = _mask_of(c, ['pine'])
        band = c.ellipse_mask(tx, cy + 1, hw - 1, 2) & m_all
        c.a[band] = p[0]
    m = _mask_of(c, ['pine'])
    _speckle_in(c, rng, m, 18, p[1], clump=1)
    sun_tips(c, rng, (c.a == p[3]), 8, p[5])
    c.outline_inside(p[0], mask=m)
    return Sprite(f'pine_{variant}', c, tx, base_y, shadow=(16, 5, 6, -1), soft_shadow=True, tags=('tree', 'ysort'))

def tree_rowan(variant=0) -> Sprite:
    rng = random.Random(400 + variant)
    W, H = 32, 52
    c = Canvas(W, H)
    base_y = H - 3; tx = W // 2
    r = R('rowan'); wood = R('wood')
    trunk(c, tx, 32, base_y, 4, wood, roots=False, knots=False, rng=rng)
    c.outline_inside(wood[0])
    clumps = [(tx - 5, 28, 9, 5), (tx + 6, 27, 8, 5), (tx, 21, 13, 9), (tx - 7, 14, 8, 6), (tx + 7, 15, 8, 6), (tx + rng.randint(-2, 2), 10, 7, 5)]
    canopy_clumps(c, clumps, r, rng, texture=0.08)
    m = _mask_of(c, ['rowan'])
    under = c.ellipse_mask(tx, 33, 8, 2) & m
    c.a[under] = r[0]
    # berry clusters (accent)
    berry = R('berry')
    for _ in range(3):
        bx, by = tx + rng.randint(-8, 8), 12 + rng.randint(-3, 6)
        if m[by, bx]:
            c.put(bx, by, berry[1]); c.put(bx + 1, by, berry[0]); c.put(bx, by + 1, berry[0]); c.put(bx + 1, by - 1, berry[2])
    c.outline_inside(r[0], mask=m)
    return Sprite(f'rowan_{variant}', c, tx, base_y, shadow=(11, 3, 4, -1), soft_shadow=True, tags=('tree', 'ysort'))

def tree_dead(variant=0) -> Sprite:
    """Bare dead tree for the forest edge / ruin: silhouette interest."""
    rng = random.Random(450 + variant)
    W, H = 40, 70
    c = Canvas(W, H)
    base_y = H - 3; tx = W // 2
    wg = R('wood_grey')
    trunk(c, tx, 24, base_y, 6, wg, rng=rng)
    # branches
    for (dx, dy, L) in ((-1, -1, 14), (1, -1, 12), (-1, -1, 8), (1, -1, 7)):
        x, y = tx, 24 + rng.randint(0, 8)
        for i in range(L):
            x += dx if rng.random() < 0.7 else 0; y += dy
            c.put(x, y, wg[2]); c.put(x + 1, y, wg[1])
        # twig
        for i in range(3):
            c.put(x + dx * i, y - i, wg[1])
    c.outline_inside(wg[0])
    return Sprite(f'dead_{variant}', c, tx, base_y, shadow=(6, 3, 3, 1), tags=('tree', 'ysort'))

# ---------------------------------------------------------------------------
# low vegetation
# ---------------------------------------------------------------------------
def shrub(variant=0, berries=False) -> Sprite:
    rng = random.Random(500 + variant)
    W, H = 28, 22
    c = Canvas(W, H)
    s = R('shrub')
    clumps = [(13 + rng.randint(-2, 2), 7, 6, 4), (8, 10, 7, 5), (19, 10, 7, 5), (14, 13, 12, 7)]
    canopy_clumps(c, clumps, s, rng, texture=0.1)
    m = _mask_of(c, ['shrub'])
    under = c.ellipse_mask(14, 19, 10, 2) & m
    c.a[under] = s[0]
    if berries:
        b = R('flower_b')
        for _ in range(5):
            bx, by = rng.randint(5, 22), rng.randint(6, 15)
            if m[by, bx]: c.put(bx, by, b[1]); c.put(bx + 1, by, b[0])
    sun_tips(c, rng, c.a == s[4], 5, s[5])
    c.outline_inside(s[0], mask=m)
    return Sprite(f'shrub_{variant}{"b" if berries else ""}', c, 14, 20, shadow=(11, 3, 2, 1), tags=('plant', 'ysort'))

def fern(variant=0) -> Sprite:
    """Six tapered fronds radiating from a crown; lit fronds face upper-left."""
    rng = random.Random(600 + variant)
    W, H = 30, 24
    c = Canvas(W, H)
    f = R('fern')
    bx, by = 15, 21
    fronds = [(-1.0, -0.3), (-0.8, -0.7), (-0.3, -1.0), (0.3, -1.0), (0.8, -0.7), (1.0, -0.3)]
    for i, (dx, dy) in enumerate(fronds):
        L = rng.randint(10, 13) + (1 if abs(dx) > 0.9 else 0)
        lit = dx < 0.2
        fill = f[3] if lit else f[2]
        tipx, tipy = bx + dx * L, by - 1 + dy * L * 0.85
        mx, my = bx + dx * L * 0.5, by - 1 + dy * L * 0.5 * 0.85
        px, py = -dy, dx
        wdt = 2.2
        c.poly([(bx, by - 1), (mx + px * wdt, my + py * wdt), (tipx, tipy), (mx - px * wdt, my - py * wdt)], fill)
        # vein + serrated edge
        for s in range(1, L):
            x = int(round(bx + dx * s)); y = int(round(by - 1 + dy * s * 0.85))
            if c.get(x, y) == fill: c.put(x, y, f[1] if not lit else f[2])
            if s % 2 == 0:
                ex, ey = int(round(x + px * wdt)), int(round(y + py * wdt))
                if c.get(ex, ey) == fill: c.put(ex, ey, 0)
        c.put(int(round(tipx)), int(round(tipy)), f[4] if lit else f[3])
    c.hline(bx - 1, bx + 1, by, f[0]); c.put(bx, by - 1, f[1])
    c.outline_inside(f[1])
    return Sprite(f'fern_{variant}', c, bx, by, shadow=(8, 2, 1, 1), tags=('plant', 'ysort'))

def flowers(variant=0, kind='w') -> Sprite:
    rng = random.Random(700 + variant + hash(kind) % 50)
    W, H = 18, 14
    c = Canvas(W, H)
    g = R('grass'); fl = R('flower_' + kind); y = R('flower_y')
    n = rng.randint(3, 5)
    for i in range(n):
        x = 3 + int(i * (W - 6) / max(1, n - 1)) + rng.randint(-1, 1)
        top = rng.randint(3, 8)
        c.vline(x, top + 1, 12, g[2])
        c.put(x + 1, 10, g[3])  # leaf
        # head: plus shape
        c.put(x, top, fl[1]); c.put(x - 1, top, fl[1]); c.put(x + 1, top, fl[0]); c.put(x, top - 1, fl[2]); c.put(x, top + 1, fl[0])
        if kind == 'w': c.put(x, top, y[1])
    return Sprite(f'flowers_{kind}{variant}', c, 9, 12, shadow=None, tags=('plant', 'ysort'))

def mushrooms(variant=0, glow=False) -> Sprite:
    rng = random.Random(800 + variant)
    W, H = 14, 10
    c = Canvas(W, H)
    cap = R('glowshroom') if glow else R('shroom'); st = R('shroom_stem')
    n = rng.randint(2, 3)
    for i in range(n):
        x = 3 + i * 4 + rng.randint(0, 1); h = rng.randint(3, 5); r = rng.randint(2, 3)
        c.rect(x, 9 - h, 2, h, st[1]); c.put(x + 1, 9 - h, st[0])
        c.ellipse(x + 0.5, 9 - h - 0.5, r, 1.6, cap[1])
        c.put(x - 1, 9 - h, cap[0]); c.put(x + 2, 9 - h, cap[0])
        c.put(x, 9 - h - 2, cap[2])
        if not glow: c.put(x + 1, 9 - h - 1, cap[3])
    return Sprite(f'{"glow" if glow else ""}shroom_{variant}', c, 7, 9, shadow=None, tags=('plant', 'ysort'))

def grass_tuft(variant=0) -> Sprite:
    rng = random.Random(850 + variant)
    c = Canvas(10, 8); g = R('grass')
    for i in range(5):
        x = 2 + i + rng.randint(0, 1); h = rng.randint(2, 5)
        c.vline(x, 7 - h, 7, g[4] if i % 2 else g[3])
        c.put(x, 7 - h, g[5] if i % 2 else g[4])
    return Sprite(f'tuft_{variant}', c, 5, 7, tags=('plant', 'ysort'))

def reeds(variant=0) -> Sprite:
    rng = random.Random(900 + variant)
    W, H = 16, 26
    c = Canvas(W, H); r = R('reed'); d = R('dirt')
    for i in range(6):
        x = 2 + i * 2 + rng.randint(0, 1); h = rng.randint(12, 22); lean = rng.choice((-1, 0, 1))
        for s in range(h):
            xx = x + (lean if s > h * 0.6 else 0)
            c.put(xx, 24 - s, r[2] if i % 2 else r[1])
        c.put(x + (lean if True else 0), 24 - h, r[3])
        if i in (1, 4):  # cattail head
            c.rect(x + lean, 24 - h + 2, 2, 4, d[1]); c.put(x + lean, 24 - h + 2, d[2])
    return Sprite(f'reeds_{variant}', c, 8, 24, shadow=None, tags=('plant', 'ysort'))

def lily_pad(variant=0) -> Sprite:
    rng = random.Random(950 + variant)
    c = Canvas(10, 8); l = R('lily')
    c.ellipse(4.5, 4, 4, 2.6, l[2]); c.ellipse(3.5, 3.3, 2.5, 1.5, l[3])
    c.put(8, 5, l[1]); c.put(7, 6, l[1]); c.put(4, 6, l[1])
    c.put(7, 3, l[2]); c.put(8, 3, 0); c.put(8, 4, l[1])   # notch
    if variant % 3 == 0:
        w = R('flower_w'); c.put(3, 2, w[2]); c.put(2, 3, w[1]); c.put(4, 3, w[1]); c.put(3, 3, R('flower_y')[1])
    return Sprite(f'lily_{variant}', c, 5, 6, shadow=None, tags=('water',))

# ---------------------------------------------------------------------------
# rocks, logs
# ---------------------------------------------------------------------------
def boulder(size='l', variant=0) -> Sprite:
    rng = random.Random(1000 + variant + {'s': 0, 'm': 10, 'l': 20}[size])
    rx, ry = {'s': (6, 4), 'm': (10, 6), 'l': (15, 9)}[size]
    W, H = rx * 2 + 8, ry * 2 + 10
    c = Canvas(W, H); st = R('stone'); mo = R('moss')
    cx, cy = W // 2, H - ry - 4
    # two overlapping lumps
    shaded_blob(c, cx, cy, rx, ry, st, light=(-0.4, -0.5), ranks=(1, 2, 3, 4))
    shaded_blob(c, cx + rx * 0.35, cy - ry * 0.25, rx * 0.6, ry * 0.75, st, light=(-0.4, -0.5), ranks=(1, 2, 3, 4))
    m = _mask_of(c, ['stone'])
    # facet lines
    for _ in range(2):
        x0 = cx + rng.randint(-rx // 2, rx // 2); y0 = cy + rng.randint(-ry // 2, 0)
        for i in range(rng.randint(3, 5)):
            if m[y0 + i, x0 + (i // 2)]: c.put(x0 + (i // 2), y0 + i, st[1])
    # moss on the shaded lower-left and on top (damp, mossy outcrop)
    mm = (c.ellipse_mask(cx - rx * 0.4, cy + ry * 0.55, rx * 0.6, ry * 0.4) | c.ellipse_mask(cx - rx * 0.1, cy - ry * 0.7, rx * 0.5, ry * 0.3)) & m
    c.a[mm] = mo[1]
    ys, xs = np.nonzero(mm)
    for k in range(len(xs)):
        if (xs[k] + ys[k]) % 3 == 0: c.put(int(xs[k]), int(ys[k]), mo[2])
    edge = np.pad(mm, 1); grown = edge[:-2, 1:-1] | edge[2:, 1:-1] | edge[1:-1, :-2] | edge[1:-1, 2:]
    ring = grown[:, :] & ~mm & m
    ys, xs = np.nonzero(ring)
    for k in range(len(xs)):
        if (xs[k] * 3 + ys[k]) % 2 == 0: c.put(int(xs[k]), int(ys[k]), mo[0])
    # base contact: dark band where the rock meets the ground
    base = c.ellipse_mask(cx + 1, cy + ry, rx * 0.9, 1.5) & m
    c.a[base] = st[0]
    c.outline_inside(st[0], mask=m)
    return Sprite(f'boulder_{size}{variant}', c, cx, cy + ry, shadow=(rx, max(2, ry // 2), 2, 1), tags=('rock', 'ysort'))

def stone_small(variant=0) -> Sprite:
    rng = random.Random(1100 + variant)
    c = Canvas(7, 5); p = R('pebble')
    c.ellipse(3, 2.5, 3, 1.8, p[1]); c.put(2, 1, p[2]); c.put(1, 2, p[2]); c.hline(2, 4, 4, p[0]); c.put(5, 3, p[0])
    if variant % 2: c.put(2, 3, R('moss')[1])
    return Sprite(f'stone_{variant}', c, 3, 4, tags=('rock', 'ysort'))

def fallen_log(variant=0) -> Sprite:
    rng = random.Random(1200 + variant)
    W, H = 44, 18
    c = Canvas(W, H); w = R('wood'); mo = R('moss')
    x0, x1, yc = 3, 38, 9
    # cylinder body
    for y in range(yc - 5, yc + 5):
        t = (y - (yc - 5)) / 9
        col = w[4] if t < 0.22 else w[3] if t < 0.55 else w[2] if t < 0.8 else w[1]
        c.hline(x0, x1, y, col)
    # end grain on the right
    c.ellipse(x1 + 1, yc, 3, 5, w[2]); c.ellipse(x1 + 1, yc, 2, 3.4, w[3]); c.ellipse(x1 + 1, yc, 1, 1.6, w[2])
    c.put(x1 + 1, yc, w[1])
    # bark cracks
    for _ in range(6):
        xx = rng.randint(x0 + 2, x1 - 3); yy = rng.randint(yc - 3, yc + 3)
        c.hline(xx, xx + rng.randint(2, 5), yy, w[1])
    # moss on top
    for _ in range(4):
        xx = rng.randint(x0 + 2, x1 - 6); L = rng.randint(3, 7)
        c.hline(xx, xx + L, yc - 5, mo[2]); c.hline(xx + 1, xx + L - 1, yc - 4, mo[1])
        c.put(xx + L // 2, yc - 6, mo[2])
    # broken stub branch
    c.rect(12, yc - 9, 3, 5, w[2]); c.put(12, yc - 9, w[3]); c.put(14, yc - 6, w[1])
    m = c.mask()
    c.outline_inside(w[0], mask=m)
    # small mushrooms growing on the shaded side
    sh = mushrooms(variant, glow=False)
    c.blit(sh.c, 24, yc - 2)
    return Sprite(f'log_{variant}', c, 20, yc + 5, shadow=(20, 3, 2, 1), tags=('prop', 'ysort'))

def stump(variant=0) -> Sprite:
    c = Canvas(16, 14); w = R('wood'); mo = R('moss')
    c.rect(3, 5, 10, 7, w[2]); c.rect(3, 5, 3, 7, w[3]); c.rect(10, 5, 3, 7, w[1])
    c.ellipse(8, 5, 5.5, 3, w[4]); c.ellipse(8, 5, 3.5, 2, w[3]); c.ellipse(8, 5, 1.5, 1, w[4]); c.put(8, 5, w[2])
    c.hline(2, 4, 12, w[1]); c.hline(11, 14, 12, w[0])
    c.put(4, 9, mo[1]); c.put(5, 10, mo[1]); c.put(4, 10, mo[2])
    c.outline_inside(w[0])
    return Sprite(f'stump_{variant}', c, 8, 12, shadow=(6, 2, 1, 1), tags=('prop', 'ysort'))

def fallen_branch(variant=0) -> Sprite:
    rng = random.Random(1300 + variant)
    c = Canvas(26, 10); w = R('wood')
    x, y = 1, 6
    for i in range(24):
        y += rng.choice((-1, 0, 0, 0, 1)) if i % 4 == 0 else 0
        y = max(2, min(8, y))
        c.put(x + i, y, w[2]); c.put(x + i, y + 1, w[1])
        if i in (6, 15): 
            for k in range(3): c.put(x + i + k, y - 1 - k, w[2])
    c.outline_inside(w[0])
    return Sprite(f'branch_{variant}', c, 13, 8, tags=('prop', 'ysort'))

# ---------------------------------------------------------------------------
# camp
# ---------------------------------------------------------------------------
def tent() -> Sprite:
    """Ridge tent, ridge running toward the camera; near gable carries the door."""
    W, H = 56, 54
    c = Canvas(W, H); cv = R('canvas'); rope = R('rope'); ti = R('tent_interior'); wd = R('wood')
    rx = 28
    far_top, far_base = 4, 26        # far gable apex / ground line (hidden)
    near_top, near_base = 22, 44     # near gable apex / ground line
    hw = 21
    # ground sheet peeking out at the hem
    c.rect(rx - hw - 2, near_base + 1, hw * 2 + 5, 2, cv[0])
    # left slope (lit) / right slope (shade): quads from near gable edge to far gable edge
    c.poly([(rx - hw, near_base), (rx, near_top), (rx, far_top), (rx - hw, far_base)], cv[4])
    c.poly([(rx, near_top), (rx + hw, near_base), (rx + hw, far_base), (rx, far_top)], cv[2])
    # fabric sag: darker creases following the slope
    for k in range(3):
        y0 = far_base + 3 + k * 6
        c.line(rx - hw + 2, y0, rx - 2, y0 - 16, cv[3])
    for k in range(2):
        y0 = far_base + 5 + k * 7
        c.line(rx + 2, y0 - 16, rx + hw - 2, y0, cv[1])
    # sun-bleached streak high on the lit slope
    c.line(rx - 12, far_base - 2, rx - 3, far_top + 4, cv[5])
    # ridge seam with stitching, pole ends at both gables
    c.vline(rx, far_top, near_top, cv[1])
    for y in range(far_top + 2, near_top, 3): c.put(rx, y, cv[5])
    c.vline(rx, far_top - 3, far_top, wd[2]); c.put(rx, far_top - 3, wd[3])
    # near gable: vertical canvas face (mid tone) with the doorway
    c.poly([(rx - hw, near_base), (rx, near_top), (rx + hw, near_base)], cv[3])
    c.line(rx - hw, near_base, rx, near_top, cv[4]); c.line(rx, near_top, rx + hw, near_base, cv[1])
    # worn patches: a sewn square and grime along the hem
    c.rect(rx + 7, near_base - 9, 5, 4, cv[1]); c.rect(rx + 8, near_base - 8, 3, 2, cv[2]); c.put(rx + 7, near_base - 9, cv[0])
    for x in range(rx - hw + 1, rx + hw, 2):
        if (x * 7) % 5 < 2: c.put(x, near_base - 1, cv[1])
    c.hline(rx - hw, rx + hw, near_base, cv[0])
    # doorway: dark interior, bedding catching a little light, flap rolled left
    c.poly([(rx, near_base - 17), (rx + 7, near_base), (rx - 7, near_base)], ti[1])
    c.poly([(rx, near_base - 15), (rx + 5, near_base), (rx - 5, near_base)], ti[0])
    c.poly([(rx + 1, near_base - 7), (rx + 4, near_base - 1), (rx - 3, near_base - 1)], ti[2])
    c.rect(rx - 9, near_base - 9, 3, 8, cv[3]); c.vline(rx - 9, near_base - 9, near_base - 2, cv[4]); c.vline(rx - 7, near_base - 9, near_base - 2, cv[1])
    c.vline(rx, near_top - 3, near_top, wd[2]); c.put(rx, near_top - 3, wd[3])
    # guy ropes from the gable corners to pegs
    for (ex, ey, px, py) in ((rx - hw + 1, near_base - 4, rx - hw - 6, near_base + 5), (rx + hw - 1, near_base - 4, rx + hw + 6, near_base + 5),
                             (rx - hw + 1, far_base - 1, rx - hw - 5, far_base - 4), (rx + hw - 1, far_base - 1, rx + hw + 5, far_base - 4)):
        c.line(ex, ey, px, py, rope[1]); c.put(px, py, wd[1]); c.put(px, py - 1, wd[2])
    c.outline_inside(cv[0], mask=_mask_of(c, ['canvas']))
    return Sprite('tent', c, rx, near_base, shadow=(27, 5, 6, -1), soft_shadow=True, tags=('structure', 'ysort'))

def campfire() -> Sprite:
    W, H = 26, 20
    c = Canvas(W, H); st = R('stone'); pb = R('pebble'); em = R('ember'); w = R('wood'); f = R('fire')
    cx, cy = 13, 13
    c.ellipse(cx, cy, 8, 4.5, em[0]); c.ellipse(cx, cy, 5, 2.5, em[1])
    # crossed logs
    c.line(cx - 5, cy + 2, cx + 5, cy - 2, w[2]); c.line(cx - 5, cy + 3, cx + 5, cy - 1, w[1])
    c.line(cx - 5, cy - 2, cx + 5, cy + 2, w[3]); c.line(cx - 5, cy - 1, cx + 5, cy + 3, w[1])
    # low flame
    c.poly([(cx, cy - 8), (cx + 3, cy - 2), (cx - 3, cy - 2)], f[1])
    c.poly([(cx, cy - 6), (cx + 2, cy - 2), (cx - 2, cy - 2)], f[2])
    c.put(cx, cy - 4, f[3]); c.put(cx + 2, cy - 6, f[1])
    # stone ring
    for i in range(9):
        a = i / 9 * math.pi * 2
        sx, sy = cx + math.cos(a) * 9, cy + math.sin(a) * 5
        c.ellipse(sx, sy, 2.2, 1.6, st[3] if sy < cy else st[2]); c.put(int(sx) - 1, int(sy) - 1, st[4]); c.put(int(sx) + 1, int(sy) + 1, st[1])
    c.outline_inside(st[0], mask=_mask_of(c, ['stone']))
    return Sprite('campfire', c, cx, cy + 5, shadow=(9, 3, 1, 1), tags=('prop', 'ysort', 'light'))

def log_seat() -> Sprite:
    c = Canvas(24, 10); w = R('wood')
    for y in range(2, 8):
        col = w[4] if y == 2 else w[3] if y < 5 else w[2] if y < 7 else w[1]
        c.hline(2, 20, y, col)
    c.ellipse(21, 5, 2, 3, w[2]); c.ellipse(21, 5, 1, 1.6, w[3])
    c.hline(5, 9, 4, w[1]); c.hline(12, 15, 6, w[1])
    c.outline_inside(w[0])
    return Sprite('log_seat', c, 12, 8, shadow=(10, 2, 1, 1), tags=('prop', 'ysort'))

def lantern_post() -> Sprite:
    W, H = 16, 34
    c = Canvas(W, H); w = R('wood'); mt = R('metal'); gl = R('lantern_glass'); rope = R('rope')
    px = 4
    c.rect(px - 1, 6, 3, 26, w[2]); c.vline(px - 1, 6, 31, w[3]); c.vline(px + 1, 6, 31, w[1])
    c.hline(px - 2, px + 2, 31, w[1])
    c.hline(px, px + 8, 6, w[2]); c.put(px + 8, 7, w[1]); c.line(px + 2, 10, px + 6, 6, w[1])   # arm + brace
    lx, ly = px + 8, 9
    c.vline(lx, 7, 9, mt[2])                                     # chain
    c.rect(lx - 3, ly, 7, 2, mt[1]); c.put(lx, ly - 1, mt[2])    # cap
    c.rect(lx - 3, ly + 2, 7, 7, gl[1]); c.rect(lx - 2, ly + 3, 5, 5, gl[2]); c.rect(lx - 1, ly + 4, 2, 2, gl[3])
    c.vline(lx - 3, ly + 2, ly + 8, mt[1]); c.vline(lx + 3, ly + 2, ly + 8, mt[0])
    c.rect(lx - 3, ly + 9, 7, 1, mt[1]); c.put(lx, ly + 10, mt[0])
    c.outline_inside(w[0], mask=_mask_of(c, ['wood']))
    return Sprite('lantern_post', c, px, 31, shadow=(3, 1.5, 1, 1), tags=('prop', 'ysort', 'light'))

def lantern_hanging() -> Sprite:
    """Small hanging lantern (for the ruin doorway / dock post)."""
    c = Canvas(9, 14); mt = R('metal'); gl = R('lantern_glass')
    lx, ly = 4, 3
    c.vline(lx, 0, 2, mt[2])
    c.rect(lx - 3, ly, 7, 2, mt[1]); c.put(lx, ly - 1, mt[2])
    c.rect(lx - 3, ly + 2, 7, 7, gl[1]); c.rect(lx - 2, ly + 3, 5, 5, gl[2]); c.rect(lx - 1, ly + 4, 2, 2, gl[3])
    c.vline(lx - 3, ly + 2, ly + 8, mt[1]); c.vline(lx + 3, ly + 2, ly + 8, mt[0])
    c.rect(lx - 3, ly + 9, 7, 1, mt[1]); c.put(lx, ly + 10, mt[0])
    return Sprite('lantern_hanging', c, lx, 13, shadow=None, tags=('prop', 'light'))

def fishing_dock() -> Sprite:
    """Weathered plank platform, shore at the left, planks running across its width."""
    W, H = 56, 34
    c = Canvas(W, H); wg = R('wood_grey'); rope = R('rope'); mt = R('metal'); w = R('wood')
    x0, x1, y0, y1 = 2, 48, 10, 24
    # post legs under the deck (seen through the water side)
    for px in (x1 - 5, x0 + 14):
        c.rect(px, y1 + 1, 3, 5, wg[1]); c.put(px, y1 + 1, wg[2])
    # deck plane: planks run top-to-bottom; alternate tones; dark gaps
    i = 0
    for x in range(x0, x1, 4):
        col = wg[3] if i % 3 != 1 else wg[2]
        c.rect(x, y0, 3, y1 - y0, col)
        c.vline(x + 3, y0, y1 - 1, wg[0])
        c.put(x + (i % 2), y0 + 2 + (i * 5) % 9, wg[1])            # worn grain
        c.put(x + 1, y0 + 1, mt[1]); c.put(x + 1, y1 - 2, mt[1])    # nails
        i += 1
    c.hline(x0, x1, y0, wg[4])                                      # lit far edge
    c.rect(x0, y1, x1 - x0, 3, wg[1]); c.hline(x0, x1, y1 + 2, wg[0])  # front face (thickness)
    # corner posts: short stubs with lit tops; far-right one carries the lantern hook
    for (px, py) in ((x1 - 5, y0 - 5), (x1 - 5, y1 - 4), (x0 + 14, y1 - 4)):
        c.rect(px, py, 3, 7, wg[2]); c.vline(px, py, py + 6, wg[3]); c.hline(px, px + 2, py, wg[4]); c.put(px + 2, py + 6, wg[0])
    c.hline(x1 - 3, x1 + 3, y0 - 7, mt[1]); c.put(x1 + 3, y0 - 6, mt[2])      # hook arm
    c.line(x1 - 4, y1 - 3, x1 + 4, y1 + 1, rope[1]); c.put(x1 + 4, y1 + 1, rope[0])   # mooring rope
    # bucket and a leaning rod
    c.rect(x0 + 5, y0 + 2, 5, 5, mt[2]); c.hline(x0 + 5, x0 + 9, y0 + 2, mt[3]); c.vline(x0 + 9, y0 + 2, y0 + 6, mt[1]); c.put(x0 + 7, y0 + 1, mt[1])
    c.line(x1 - 12, y1 - 1, x1 + 2, y0 - 12, w[3]); c.put(x1 + 2, y0 - 12, w[4])
    c.outline_inside(wg[0], mask=_mask_of(c, ['wood_grey']))
    return Sprite('dock', c, x0 + 2, y1 + 3, shadow=(24, 3, 3, 3), tags=('structure', 'ysort'))

def _stone_wall(c, x0, y0, w, h_face, top_profile, ramp, rng, mossy=True):
    """Wall with a visible top face (lit) and front face (stone courses).
    top_profile: list of heights (px) above y0 for each column group."""
    top = ramp[4]; face = ramp[2]; mort = ramp[0]; lt = ramp[3]
    # broken crest: per 4-px column
    for cx in range(x0, x0 + w):
        k = (cx - x0) * len(top_profile) // w
        hgt = top_profile[k]
        c.vline(cx, y0 - hgt, y0 + h_face, face)
        c.put(cx, y0 - hgt, top); c.put(cx, y0 - hgt + 1, top)
        c.put(cx, y0 - hgt + 2, lt)
    # stone courses
    for cy in range(y0 - max(top_profile) + 3, y0 + h_face, 4):
        off = 0 if (cy // 4) % 2 == 0 else 3
        for cx in range(x0 + off, x0 + w, 7):
            if c.get(cx, cy) == face:
                c.put(cx, cy, mort)
            for xx in range(cx, min(x0 + w, cx + 7)):
                if c.get(xx, cy + 3) == face: c.put(xx, cy + 3, mort)
                if c.get(xx, cy) == face and (xx - cx) in (1, 2): c.put(xx, cy, lt)
    c.hline(x0, x0 + w - 1, y0 + h_face, mort)
    if mossy:
        mo = R('moss')
        for _ in range(w // 5):
            xx = rng.randint(x0, x0 + w - 2); yy = rng.randint(y0 + h_face - 5, y0 + h_face - 1)
            c.put(xx, yy, mo[1]); c.put(xx + 1, yy, mo[0]); c.put(xx, yy - 1, mo[2])

def ruin_back_wall() -> Sprite:
    rng = random.Random(1500)
    W, H = 96, 44
    c = Canvas(W, H); ru = R('ruin'); mo = R('moss'); gl = R('lantern_glass'); wg = R('wood_grey')
    y0, h = 14, 22
    # left segment, doorway gap, right segment (tall near the corner)
    _stone_wall(c, 2, y0, 34, h, [6, 9, 12, 10, 7, 11, 8, 5], ru, rng)
    _stone_wall(c, 52, y0, 42, h, [4, 8, 12, 13, 11, 9, 6, 3], ru, rng)
    # doorway: jambs + a surviving lintel stone
    c.vline(35, y0 - 2, y0 + h, ru[1]); c.vline(52, y0 - 1, y0 + h, ru[1])
    c.rect(34, y0 - 4, 20, 3, ru[3]); c.hline(34, 53, y0 - 4, ru[4]); c.hline(34, 53, y0 - 2, ru[1])
    # window hole in the right segment
    c.rect(70, y0 + 3, 7, 7, 0); c.vline(70, y0 + 3, y0 + 9, ru[1]); c.hline(70, 76, y0 + 3, ru[1])
    # ivy climbing from the base, over the crest on the left
    for (sx, L) in ((6, 16), (20, 11), (60, 9), (84, 14)):
        x, y = sx, y0 + h - 1
        for i in range(L):
            x += rng.choice((-1, 0, 0, 1)); y -= 1
            if c.get(x, y) in ru: c.put(x, y, mo[1])
            if rng.random() < 0.6 and c.get(x + 1, y) in ru: c.put(x + 1, y, mo[2])
            if rng.random() < 0.3 and c.get(x - 1, y + 1) in ru: c.put(x - 1, y + 1, mo[0])
    # a sagging beam leaning across the doorway top
    c.line(36, y0 - 3, 50, y0 + 5, wg[2]); c.line(36, y0 - 2, 50, y0 + 6, wg[1])
    m = c.mask()
    c.outline_inside(ru[0], mask=_mask_of(c, ['ruin']))
    return Sprite('ruin_back', c, 48, y0 + h, shadow=(46, 4, 4, 3), tags=('structure', 'ysort'))

def ruin_side_wall() -> Sprite:
    """Low wall running toward the camera: irregular stone top, a short lit
    west face, crumbling to rubble at the south end."""
    rng = random.Random(1501)
    W, H = 22, 58
    c = Canvas(W, H); ru = R('ruin'); mo = R('moss')
    x0, wdt = 5, 10
    # top face, broken into irregular blocks
    c.rect(x0, 6, wdt, 40, ru[3])
    y = 6
    while y < 44:
        h = rng.randint(4, 7)
        c.hline(x0, x0 + wdt - 1, y + h, ru[1])
        sx = x0 + rng.randint(3, 6)
        c.vline(sx, y + 1, y + h - 1, ru[1])
        c.put(x0 + rng.randint(0, wdt - 1), y + rng.randint(1, max(1, h - 1)), ru[4])
        y += h + 1
    # west face catches light; east edge in shade; crest nibbled
    c.vline(x0 - 1, 8, 46, ru[4]); c.vline(x0 - 2, 12, 44, ru[2])
    c.vline(x0 + wdt, 8, 47, ru[1])
    for k in range(5):
        xx = x0 + rng.randint(0, wdt - 2); yy = rng.choice((6, 7))
        c.put(xx, yy, 0); c.put(xx + 1, yy, 0)
    # crumbling south end: a short front face then rubble
    c.rect(x0 - 1, 46, wdt + 2, 6, ru[2]); c.hline(x0 - 1, x0 + wdt, 49, ru[1]); c.put(x0 + 3, 47, ru[1]); c.put(x0 + 7, 50, ru[1])
    c.ellipse(x0 + 2, 54, 3.5, 2, ru[2]); c.ellipse(x0 + 8, 55, 3, 1.8, ru[3]); c.ellipse(x0 + 5, 56, 2, 1.2, ru[1])
    for _ in range(6):
        c.put(rng.randint(x0, x0 + wdt - 1), rng.randint(30, 50), mo[1])
    c.put(x0 + 1, 45, mo[2]); c.put(x0 + 2, 46, mo[0]); c.put(x0 + wdt - 1, 40, mo[0])
    c.outline_inside(ru[0])
    return Sprite('ruin_side', c, x0 + 5, 56, shadow=(8, 3, 3, 1), tags=('structure', 'ysort'))

def rubble(variant=0) -> Sprite:
    rng = random.Random(1600 + variant)
    c = Canvas(26, 14); rb = R('rubble'); ru = R('ruin'); mo = R('moss')
    for _ in range(7):
        x, y = rng.randint(3, 22), rng.randint(5, 11); r = rng.randint(2, 4)
        c.ellipse(x, y, r, r * 0.6, rb[1]); c.put(x - 1, y - 1, rb[2]); c.put(x + 1, y + 1, rb[0])
    c.rect(8, 3, 6, 4, ru[3]); c.hline(8, 13, 3, ru[4]); c.hline(8, 13, 6, ru[1])   # one squared block
    c.put(5, 11, mo[1]); c.put(16, 12, mo[1]); c.put(17, 12, mo[2])
    c.outline_inside(rb[0])
    return Sprite(f'rubble_{variant}', c, 13, 12, shadow=(11, 2, 1, 1), tags=('prop', 'ysort'))

def fallen_beam() -> Sprite:
    c = Canvas(40, 12); wg = R('wood_grey'); mo = R('moss')
    c.poly([(2, 3), (36, 6), (36, 10), (2, 7)], wg[2])
    c.line(2, 3, 36, 6, wg[3]); c.line(2, 7, 36, 10, wg[0])
    c.rect(36, 5, 3, 6, wg[1]); c.put(37, 6, wg[2])
    for x in (8, 18, 26): c.put(x, 5, wg[1]); c.put(x + 1, 5, wg[1])
    c.put(12, 4, mo[1]); c.put(13, 4, mo[2]); c.put(28, 6, mo[1])
    c.outline_inside(wg[0])
    return Sprite('beam', c, 20, 10, shadow=(17, 2, 1, 1), tags=('prop', 'ysort'))

# ---------------------------------------------------------------------------
# scale reference (debug only - not part of the world art)
# ---------------------------------------------------------------------------
def mannequin() -> Sprite:
    c = Canvas(12, 22); cv = R('canvas'); w = R('wood'); st = R('shroom_stem')
    c.ellipse(6, 4, 3, 3.5, st[2]); c.rect(3, 8, 6, 8, cv[2]); c.rect(3, 16, 2, 5, w[2]); c.rect(7, 16, 2, 5, w[2])
    c.rect(4, 1, 5, 2, w[1])  # hair/cap
    c.outline_inside(w[0])
    return Sprite('mannequin', c, 6, 21, shadow=(4, 1.5, 1, 0), tags=('debug', 'ysort'))

# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------
def build_library() -> dict[str, Sprite]:
    lib = {}
    def add(s): lib[s.name] = s
    for v in range(4): add(tree_oak(v))
    for v in range(2): add(tree_birch(v))
    for v in range(2): add(tree_pine(v))
    for v in range(2): add(tree_rowan(v))
    add(tree_dead(0))
    for v in range(3): add(shrub(v)); 
    add(shrub(3, berries=True))
    for v in range(3): add(fern(v))
    for k in ('w', 'p', 'b'): add(flowers(0, k)); add(flowers(1, k))
    for v in range(2): add(mushrooms(v)); add(mushrooms(v, glow=True))
    for v in range(3): add(grass_tuft(v))
    for v in range(2): add(reeds(v))
    for v in range(4): add(lily_pad(v))
    for sz in 'sml':
        for v in range(2): add(boulder(sz, v))
    for v in range(2): add(stone_small(v))
    add(fallen_log(0)); add(stump(0)); add(fallen_branch(0)); add(fallen_branch(1))
    add(tent()); add(campfire()); add(log_seat()); add(lantern_post()); add(lantern_hanging()); add(fishing_dock())
    add(ruin_back_wall()); add(ruin_side_wall()); add(rubble(0)); add(rubble(1)); add(fallen_beam())
    add(mannequin())
    return lib


# ===========================================================================
# Prompt 03 additions: vegetation library, winter variants, generic snow caps
# ===========================================================================
def sapling(species='oak', variant=0) -> Sprite:
    """Young tree: thin whip of a trunk, three small leaf clusters."""
    rng = random.Random(1700 + variant + hash(species) % 31)
    W, H = 22, 32
    c = Canvas(W, H); base_y = H - 2; tx = W // 2
    ramp = R(species); wood = R('wood') if species != 'birch' else R('bark_birch')
    c.vline(tx, 14, base_y, wood[2]); c.vline(tx + 1, 16, base_y, wood[1]); c.put(tx - 1, base_y, wood[1])
    if species == 'birch':
        c.put(tx, 20, wood[0]); c.put(tx, 26, wood[0])
    lobes = [(tx + 3, 12, 6, 4), (tx - 4, 9, 6, 4), (tx + rng.randint(-1, 1), 5, 5, 4)]
    canopy_clusters(c, lobes, ramp, rng)
    m = _mask_of(c, [species])
    c.outline_inside(ramp[0], mask=m)
    return Sprite(f'sapling_{species}{variant}', c, tx, base_y, shadow=(5, 2, 2, 0), tags=('tree', 'ysort', 'sapling'))

def hedge(variant=0) -> Sprite:
    """A long run of shrub clusters, flat-topped: hedgerow / thicket."""
    rng = random.Random(1800 + variant)
    W, H = 60, 24
    c = Canvas(W, H); s = R('shrub')
    lobes = []
    for i in range(6):
        x = 7 + i * 9 + rng.randint(-1, 1)
        lobes.append((x, 9 + rng.randint(-1, 1), 7, 5))
    for i in range(5):
        lobes.append((11 + i * 9, 15, 8, 5))
    canopy_clusters(c, lobes, s, rng)
    m = _mask_of(c, ['shrub'])
    under = c.ellipse_mask(30, 21, 28, 2) & m
    c.a[under] = s[0]
    if variant % 2:
        b = R('flower_w')
        for _ in range(6):
            bx, by = rng.randint(4, 56), rng.randint(5, 14)
            if m[by, bx]: c.put(bx, by, b[2]); c.put(bx + 1, by, b[1])
    sun_tips(c, rng, c.a == s[4], 8, s[5])
    c.outline_inside(s[0], mask=m)
    return Sprite(f'hedge_{variant}', c, 30, 22, shadow=(27, 3, 2, 1), tags=('plant', 'ysort', 'solid'))

def tall_grass(variant=0) -> Sprite:
    rng = random.Random(1900 + variant)
    W, H = 22, 20
    c = Canvas(W, H); g = R('grass'); rd = R('reed')
    bx, by = 11, 18
    for i in range(8):
        lean = (i - 3.5) * 0.45
        h = rng.randint(9, 15)
        x = bx + rng.randint(-2, 2)
        col = g[4] if i % 3 else g[3]
        for s in range(h):
            xx = int(round(x + lean * (s / h) ** 1.6 * 3)); yy = by - s
            c.put(xx, yy, col if s < h - 3 else (rd[3] if i % 2 else g[5]))
    c.hline(bx - 3, bx + 3, by, g[2])
    return Sprite(f'tallgrass_{variant}', c, bx, by, shadow=None, tags=('plant', 'ysort'))

def roots(variant=0) -> Sprite:
    """Exposed roots radiating from a trunk base, laid on the ground layer."""
    rng = random.Random(2000 + variant)
    W, H = 48, 18
    c = Canvas(W, H); w = R('wood')
    ox, oy = 24, 4
    for (dx, dy, L) in ((-1.0, 0.45, 18), (-0.6, 0.8, 12), (0.5, 0.85, 11), (1.0, 0.4, 19), (0.15, 1.0, 8)):
        x, y = float(ox), float(oy)
        for s in range(L):
            x += dx * (1 + rng.random() * 0.3); y += dy * (0.6 + rng.random() * 0.4)
            xi, yi = int(round(x)), int(round(y))
            thick = 2 if s < L * 0.6 else 1
            for k in range(thick):
                c.put(xi, yi + k, w[3] if k == 0 else w[2])
            c.put(xi, yi + thick, w[1])
    c.outline_inside(w[0])
    return Sprite(f'roots_{variant}', c, ox, oy, shadow=None, tags=('ground',))

def leaf_pile(variant=0) -> Sprite:
    rng = random.Random(2100 + variant)
    W, H = 24, 12
    c = Canvas(W, H); ll = R('leaf_litter')
    for _ in range(14):
        x, y = rng.randint(2, 20), rng.randint(2, 9)
        if abs(x - 12) / 11 + abs(y - 6) / 5 > 1.2: continue
        col = ll[rng.choice((1, 2, 2, 3))]
        c.put(x, y, col); c.put(x + 1, y, ll[rng.choice((1, 2))])
        if rng.random() < 0.5: c.put(x + 1, y - 1, col)
    return Sprite(f'leafpile_{variant}', c, 12, 10, shadow=None, tags=('ground',))

def hollow_log(variant=0) -> Sprite:
    rng = random.Random(2200 + variant)
    W, H = 44, 20
    c = Canvas(W, H); w = R('wood'); wg = R('wood_grey'); mo = R('moss')
    x0, x1, yc = 4, 38, 10
    for y in range(yc - 5, yc + 5):
        t = (y - (yc - 5)) / 9
        col = wg[4] if t < 0.22 else wg[3] if t < 0.55 else wg[2] if t < 0.8 else wg[1]
        c.hline(x0, x1, y, col)
    # hollow end: dark opening with a lit rim
    c.ellipse(x1 + 1, yc, 3.5, 5, wg[2]); c.ellipse(x1 + 1, yc, 2.3, 3.4, w[0]); c.put(x1 - 1, yc - 3, wg[3])
    # decay: bark gaps showing warm wood, moss blankets
    for _ in range(4):
        xx = rng.randint(x0 + 2, x1 - 6); L = rng.randint(2, 5); yy = rng.randint(yc - 2, yc + 3)
        c.hline(xx, xx + L, yy, w[2]); c.put(xx, yy + 1, w[1])
    for _ in range(5):
        xx = rng.randint(x0 + 1, x1 - 8); L = rng.randint(4, 9)
        c.hline(xx, xx + L, yc - 5, mo[2]); c.hline(xx + 1, xx + L - 1, yc - 4, mo[1]); c.hline(xx + 2, xx + L - 3, yc - 3, mo[1])
        c.put(xx + L // 2, yc - 6, mo[2])
    c.outline_inside(wg[0], mask=c.mask())
    sh = mushrooms(variant + 1)
    c.blit(sh.c, 14, yc - 1)
    return Sprite(f'hollowlog_{variant}', c, 20, yc + 5, shadow=(20, 3, 2, 1), tags=('prop', 'ysort', 'solid'))

def boulder_mossy(size='m', variant=0) -> Sprite:
    b = boulder(size, variant + 5)
    c = b.c; rng = random.Random(2300 + variant); mo = R('moss'); st = R('stone')
    m = _mask_of(c, ['stone'])
    rx = c.w // 2 - 4
    blanket = (c.ellipse_mask(b.ox - rx * 0.2, b.oy - c.h * 0.45, rx * 0.85, c.h * 0.22) | c.ellipse_mask(b.ox - rx * 0.6, b.oy - c.h * 0.2, rx * 0.5, c.h * 0.2)) & m
    ys, xs = np.nonzero(blanket)
    for k in range(len(xs)):
        x, y = int(xs[k]), int(ys[k])
        c.put(x, y, mo[2] if (x * 3 + y) % 4 == 0 else mo[1])
    p = np.pad(blanket, 1); grown = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    ys, xs = np.nonzero(grown & ~blanket & m)
    for k in range(len(xs)):
        if (xs[k] + ys[k]) % 2 == 0: c.put(int(xs[k]), int(ys[k]), mo[0])
    c.outline_inside(st[0], mask=m)
    return Sprite(f'boulder_mossy_{size}{variant}', c, b.ox, b.oy, shadow=b.shadow, tags=('rock', 'ysort', 'solid'))

def tree_willow(variant=0) -> Sprite:
    """Weeping crown: a dome of clusters with long hanging strands. Belongs at water."""
    rng = random.Random(2400 + variant)
    W, H = 68, 82
    c = Canvas(W, H); base_y = H - 4; tx = W // 2
    b = R('birch'); wood = R('wood')
    trunk(c, tx, 40, base_y, 8, wood, rng=rng)
    c.outline_inside(wood[0])
    cx, cy = tx, 22
    lobes = [(cx - 12, cy + 6, 14, 8), (cx + 12, cy + 6, 14, 8), (cx, cy, 20, 11), (cx - 6, cy - 9, 12, 7), (cx + 7, cy - 10, 12, 7), (cx, cy - 15, 9, 5)]
    canopy_clusters(c, lobes, b, rng, light=(-0.4, -0.5))
    m = _mask_of(c, ['birch'])
    # hanging strands from the crown's lower edge
    ys, xs = np.nonzero(m)
    for sx in range(cx - 26, cx + 27, 3):
        col_ys = ys[xs == sx]
        if not len(col_ys): continue
        y0 = int(col_ys.max())
        L = rng.randint(12, 26) - abs(sx - cx) // 3
        if L < 6: continue
        lit = sx < cx
        for s in range(L):
            x = sx + (1 if (s // 5) % 2 and not lit else 0)
            c.put(x, y0 + s, b[3] if lit and s < L - 4 else b[2] if s < L - 4 else b[4])
            if s % 4 == 2: c.put(x + (1 if lit else -1), y0 + s, b[1])
    c.outline_inside(b[0], mask=_mask_of(c, ['birch']))
    return Sprite(f'willow_{variant}', c, tx, base_y, shadow=(24, 6, 8, -1), soft_shadow=True, tags=('tree', 'ysort'))

def arrowhead(variant=0) -> Sprite:
    """Aquatic plant with broad arrow-shaped leaves, for shallow water."""
    rng = random.Random(2500 + variant)
    c = Canvas(14, 16); l = R('lily')
    for (x, h, lean) in ((4, 12, -1), (8, 14, 1), (6, 9, 0)):
        c.vline(x, 15 - h + 4, 15, l[1])
        top = 15 - h
        c.poly([(x + lean, top), (x + 3, top + 5), (x, top + 4), (x - 3, top + 5)], l[2])
        c.put(x + lean, top + 1, l[3]); c.put(x - 1, top + 3, l[1])
    return Sprite(f'arrowhead_{variant}', c, 6, 15, shadow=None, tags=('plant', 'ysort', 'water'))

def flowers_more(variant=0, kind='r') -> Sprite:
    """Poppy-red ('r') and yellow ('y') wildflowers."""
    rng = random.Random(760 + variant + hash(kind) % 50)
    W, H = 18, 14
    c = Canvas(W, H); g = R('grass')
    fl = R('berry') if kind == 'r' else R('flower_y')
    n = rng.randint(3, 4)
    for i in range(n):
        x = 3 + int(i * (W - 6) / max(1, n - 1)) + rng.randint(-1, 1)
        top = rng.randint(3, 8)
        c.vline(x, top + 1, 12, g[2]); c.put(x - 1, 11, g[3])
        c.put(x, top, fl[1]); c.put(x - 1, top, fl[1]); c.put(x + 1, top, fl[0]); c.put(x, top - 1, fl[2]); c.put(x, top + 1, fl[0])
        if kind == 'r': c.put(x, top, R('wood')[0])
        else: c.put(x, top, R('leaf_litter')[2])
    return Sprite(f'flowers_{kind}{variant}', c, 9, 12, shadow=None, tags=('plant', 'ysort'))

# ---------------------------------------------------------------------------
# winter
# ---------------------------------------------------------------------------
def snowcap(sprite: Sprite, depth=2, name=None) -> Sprite:
    """Generic winter variant: snow settles on every upward-facing surface.
    Pixels whose upper neighbour is transparent get a snow crest; the row
    beneath gets a cooler shade. Works for rocks, logs, stumps, pines,
    shrubs, structures."""
    c = sprite.c.copy(); sn = R('snow')
    m = c.mask()
    p = np.pad(m, 1)
    top = m & ~p[:-2, 1:-1]
    ys, xs = np.nonzero(top)
    for k in range(len(xs)):
        x, y = int(xs[k]), int(ys[k])
        # skip thin verticals (trunk edges, stems): need a run of top pixels
        if not (top[y, max(0, x - 1)] or top[y, min(c.w - 1, x + 1)]): continue
        c.put(x, y, sn[4] if (x + y) % 3 else sn[3])
        if depth > 1 and y + 1 < c.h and m[y + 1, x] and not top[y + 1, x]:
            c.put(x, y + 1, sn[3] if (x % 2) else sn[2])
    return Sprite(name or (sprite.name + '_winter'), c, sprite.ox, sprite.oy, sprite.shadow, sprite.soft_shadow, sprite.tags + ('winter',))

def tree_oak_winter(variant=0) -> Sprite:
    """Bare oak: branching crown with snow on the upper sides of the limbs."""
    rng = random.Random(2600 + variant)
    W, H = 72, 80
    c = Canvas(W, H); base_y = H - 4; tx = W // 2 + rng.randint(-2, 2)
    wood = R('wood'); sn = R('snow')
    trunk(c, tx, 44, base_y, 10 + rng.randint(0, 2), wood, rng=rng)
    def limb(x, y, ang, L, thick):
        for s in range(L):
            x += math.cos(ang); y += math.sin(ang)
            xi, yi = int(round(x)), int(round(y))
            for k in range(thick): c.put(xi + k, yi, wood[2] if k == 0 else wood[1])
            if rng.random() < 0.08: ang += rng.uniform(-0.35, 0.35)
        return x, y
    # main limbs fan out from the trunk top
    for (ang, L) in ((-2.55, 18), (-2.2, 22), (-1.85, 25), (-1.55, 27), (-1.25, 25), (-0.95, 22), (-0.6, 18)):
        a = ang + rng.uniform(-0.1, 0.1)
        ex, ey = limb(tx + rng.randint(-2, 2), 46, a, L, 2)
        for _ in range(3):                            # secondary twigs
            ex2, ey2 = limb(ex - math.cos(a) * rng.randint(4, 10), ey - math.sin(a) * rng.randint(4, 10), a + rng.uniform(-0.9, 0.9), rng.randint(6, 11), 1)
            limb(ex2, ey2, a + rng.uniform(-1.0, 1.0), rng.randint(3, 6), 1)
        limb(ex, ey, a + rng.uniform(-0.5, 0.5), rng.randint(5, 9), 1)
    c.outline_inside(wood[0])
    s = snowcap(Sprite('tmp', c, tx, base_y), depth=1)
    return Sprite(f'oak_winter_{variant}', s.c, tx, base_y, shadow=(14, 4, 6, -1), soft_shadow=True, tags=('tree', 'ysort', 'winter'))

def tree_birch_winter(variant=0) -> Sprite:
    rng = random.Random(2700 + variant)
    W, H = 44, 84
    c = Canvas(W, H); base_y = H - 3; tx = W // 2
    bark = R('bark_birch')
    for y in range(40, base_y + 1):
        fl = 1 if y > base_y - 3 else 0
        c.hline(tx - 2 - fl, tx + 2 + fl, y, bark[2]); c.put(tx - 2 - fl, y, bark[3]); c.hline(tx + 1, tx + 2 + fl, y, bark[1])
    for _ in range(6):
        yy = rng.randint(42, base_y - 4); xx = tx - 2 + rng.randint(0, 2); c.hline(xx, xx + rng.randint(1, 2), yy, bark[0])
    def limb(x, y, ang, L):
        for s in range(L):
            x += math.cos(ang); y += math.sin(ang)
            c.put(int(round(x)), int(round(y)), bark[1])
            if rng.random() < 0.1: ang += rng.uniform(-0.3, 0.3)
        return x, y
    c.vline(tx, 14, 40, bark[2]); c.vline(tx + 1, 20, 40, bark[1])
    for (ang, L, y0) in ((-2.2, 16, 38), (-1.0, 15, 34), (-2.0, 13, 28), (-1.2, 12, 24), (-1.8, 10, 18), (-1.3, 9, 16)):
        ex, ey = limb(tx, y0, ang + rng.uniform(-0.15, 0.15), L)
        limb(ex, ey, ang + rng.uniform(-0.6, 0.6), rng.randint(3, 6))
    c.outline_inside(bark[0])
    s = snowcap(Sprite('tmp', c, tx, base_y), depth=1)
    return Sprite(f'birch_winter_{variant}', s.c, tx, base_y, shadow=(9, 3, 5, -1), soft_shadow=True, tags=('tree', 'ysort', 'winter'))

def tree_willow_winter(variant=0) -> Sprite:
    """Bare weeping crown: grey limbs arching out, thin strands hanging, snow on the arches."""
    rng = random.Random(2800 + variant)
    W, H = 68, 82
    c = Canvas(W, H); base_y = H - 4; tx = W // 2
    wood = R('wood'); wg = R('wood_grey')
    trunk(c, tx, 40, base_y, 8, wood, rng=rng)
    c.vline(tx, 22, 40, wood[2]); c.vline(tx + 1, 24, 40, wood[1])
    for (ang, L) in ((-2.7, 22), (-2.3, 20), (-1.9, 16), (-1.25, 16), (-0.85, 20), (-0.45, 22)):
        x, y = float(tx), 26.0; a = ang
        for s in range(L):
            x += math.cos(a); y += math.sin(a); a += 0.09      # arch over and down
            c.put(int(round(x)), int(round(y)), wg[2]); c.put(int(round(x)), int(round(y)) + 1, wg[1])
            if s % 3 == 1 and s > 3:
                sl = rng.randint(10, 24)
                for k in range(sl):
                    c.put(int(round(x)) + (k // 7) % 2, int(round(y)) + 2 + k, wg[1] if k % 3 else wg[2])
    c.outline_inside(wg[0], mask=_mask_of(c, ['wood_grey']))
    s = snowcap(Sprite('tmp', c, tx, base_y), depth=1)
    return Sprite(f'willow_winter_{variant}', s.c, tx, base_y, shadow=(14, 4, 6, -1), soft_shadow=True, tags=('tree', 'ysort', 'winter'))

def ice_hole(variant=0) -> Sprite:
    """A hole cut in the pond ice, dark water ringed with chipped ice."""
    c = Canvas(14, 10); ice = R('ice'); w = R('water')
    c.ellipse(7, 5, 6, 3.5, ice[4]); c.ellipse(7, 5, 4.5, 2.5, w[0]); c.ellipse(6.5, 4.5, 2, 1, w[1])
    c.put(2, 3, ice[3]); c.put(12, 6, ice[3]); c.put(7, 1, ice[3])
    return Sprite(f'ice_hole_{variant}', c, 7, 7, shadow=None, tags=('ground', 'event'))

def stool(variant=0) -> Sprite:
    c = Canvas(10, 12); w = R('wood')
    c.rect(1, 2, 8, 3, w[4]); c.hline(1, 8, 4, w[2]); c.rect(1, 5, 2, 6, w[1]); c.rect(7, 5, 2, 6, w[1]); c.put(2, 2, w[5])
    c.outline_inside(w[0])
    return Sprite(f'stool_{variant}', c, 5, 11, shadow=(4, 1.5, 1, 0), tags=('prop', 'ysort', 'event'))

def bench() -> Sprite:
    c = Canvas(30, 12); w = R('wood')
    c.rect(1, 3, 28, 3, w[4]); c.hline(1, 28, 5, w[2]); c.rect(3, 6, 2, 5, w[1]); c.rect(25, 6, 2, 5, w[1]); c.hline(2, 10, 3, w[5])
    c.outline_inside(w[0])
    return Sprite('bench', c, 15, 11, shadow=(13, 2, 1, 0), tags=('prop', 'ysort', 'event', 'solid'))

def string_light_post(variant=0) -> Sprite:
    """Post with a short garland of three small lanterns (string lights for gatherings)."""
    c = Canvas(26, 34); w = R('wood'); gl = R('lantern_glass'); mt = R('metal')
    c.rect(3, 6, 3, 26, w[2]); c.vline(3, 6, 31, w[3]); c.vline(5, 6, 31, w[1]); c.hline(2, 6, 31, w[1])
    pts = [(6, 6), (11, 9), (17, 10), (23, 8)]
    for i in range(len(pts) - 1): c.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], mt[2])
    for (x, y) in pts[1:]:
        c.rect(x - 1, y + 1, 3, 3, gl[1]); c.put(x, y + 2, gl[2]); c.put(x, y + 1, mt[1])
    c.outline_inside(w[0], mask=_mask_of(c, ['wood']))
    return Sprite(f'stringlights_{variant}', c, 4, 31, shadow=(3, 1.5, 1, 0), tags=('prop', 'ysort', 'event', 'light'))

def icicles(sprite: Sprite, name=None) -> Sprite:
    """Winter structures: short icicles under horizontal overhangs (pixels whose lower neighbour is transparent)."""
    c = sprite.c.copy(); ice = R('ice'); m = c.mask(); p = np.pad(m, 1)
    under = m & ~p[2:, 1:-1]
    rng = random.Random(len(sprite.name))
    ys, xs = np.nonzero(under)
    for k in range(len(xs)):
        x, y = int(xs[k]), int(ys[k])
        if y < c.h - 4 and under[y, max(0, x - 1)] and under[y, min(c.w - 1, x + 1)] and rng.random() < 0.18:
            L = rng.randint(2, 4)
            for i in range(L):
                if y + 1 + i < c.h and not m[y + 1 + i, x]: c.put(x, y + 1 + i, ice[3] if i < L - 1 else ice[4])
    return Sprite(name or sprite.name, c, sprite.ox, sprite.oy, sprite.shadow, sprite.soft_shadow, sprite.tags)

def fern_winter(variant=0) -> Sprite:
    """Dead fern: fronds drooped flat, brown, dusted with snow."""
    base = fern(variant); c = Canvas(base.w, base.h)
    a = base.c.a; ll = R('leaf_litter'); fr = R('fern')
    # drop every frond row by 2 and recolour to litter browns
    c.a[2:, :] = a[:-2, :]
    for src, dst in zip(fr, [ll[0], ll[1], ll[1], ll[2], ll[3]]): c.a[c.a == src] = dst
    return snowcap(Sprite(f'fern_{variant}_winter', c, base.ox, base.oy, base.shadow, base.soft_shadow, base.tags + ('winter',)), depth=1, name=f'fern_{variant}_winter')

def reeds_winter(variant=0) -> Sprite:
    base = reeds(variant); c = base.c.copy(); rd = R('reed'); ll = R('leaf_litter'); sn = R('snow')
    for src, dst in zip(rd, [ll[0], ll[1], ll[2], ll[3]]): c.a[c.a == src] = dst
    ys, xs = np.nonzero(c.a != 0)
    for k in range(len(xs)):
        if (xs[k] + ys[k]) % 5 == 0: c.a[ys[k], xs[k]] = sn[3]
    return Sprite(f'reeds_{variant}_winter', c, base.ox, base.oy, base.shadow, base.soft_shadow, base.tags + ('winter',))

def build_library_extended(lib: dict) -> dict:
    def add(s): lib[s.name] = s
    for sp in ('oak', 'birch'):
        for v in range(2): add(sapling(sp, v))
    add(hedge(0)); add(hedge(1))
    for v in range(3): add(tall_grass(v))
    for v in range(2): add(roots(v)); add(leaf_pile(v)); add(hollow_log(v))
    for sz in 'ml':
        for v in range(2): add(boulder_mossy(sz, v))
    add(tree_willow(0)); add(tree_willow(1))
    for v in range(2): add(arrowhead(v))
    for k in ('r', 'y'): add(flowers_more(0, k)); add(flowers_more(1, k))
    # winter variants
    for v in range(2): add(tree_oak_winter(v)); add(tree_birch_winter(v)); add(tree_willow_winter(v))
    for n in ('pine_0', 'pine_1', 'shrub_0', 'shrub_1', 'shrub_2', 'boulder_l0', 'boulder_m0', 'boulder_s0', 'log_0', 'stump_0', 'tent', 'dock', 'ruin_back', 'ruin_side', 'rubble_0', 'beam', 'hedge_0', 'dead_0', 'rowan_0'):
        if n in lib: add(snowcap(lib[n]))
    for n in ('tent', 'dock', 'ruin_back', 'ruin_side', 'beam'):          # icicles under overhangs
        if n + '_winter' in lib: lib[n + '_winter'] = icicles(lib[n + '_winter'])
    for v in range(3): add(fern_winter(v))
    for v in range(2): add(reeds_winter(v))
    for v in range(2): add(ice_hole(v)); add(stool(v)); add(string_light_post(v))
    add(bench())
    return lib


# ===========================================================================
# Prompt 07: resource node sprites (full / depleted / regrowing states)
# ===========================================================================
def node_sprites():
    """Returns {kind: {state: Sprite}} for the world's gatherable nodes.
    States: 'full', 'depleted', 'regrow'. Nocturnal kinds glow via emissive families."""
    out = {}
    def S(name, c, ox, oy, tags=()): return Sprite(name, c, ox, oy, shadow=None, tags=('node',) + tags)
    w, st, pb, mo, g, sh, ss, gl, fw, fb, br, ll, rd, mt, mr, cv, mi = (R('wood'), R('stone'), R('pebble'), R('moss'), R('grass'), R('shroom'), R('shroom_stem'), R('glowshroom'), R('flower_w'), R('flower_b'), R('berry'), R('leaf_litter'), R('reed'), R('metal'), R('metal_rust'), R('canvas'), R('mist'))
    # branch pile
    c = Canvas(18, 10); c.line(2, 7, 14, 3, w[3]); c.line(2, 8, 14, 4, w[1]); c.line(4, 4, 15, 8, w[2]); c.line(5, 5, 16, 9, w[1]); c.line(8, 2, 10, 8, w[2]); c.outline_inside(w[0])
    d = Canvas(18, 10); d.line(5, 7, 12, 5, w[2]); d.put(5, 8, w[1]); d.put(12, 6, w[1]); d.outline_inside(w[0])
    out['branch_pile'] = {'full': S('node_branch_full', c, 9, 9), 'depleted': S('node_branch_dep', d, 9, 9), 'regrow': S('node_branch_dep', d, 9, 9)}
    # stone pile
    c = Canvas(16, 10); [c.ellipse(x, y, rx, ry, pb[1]) for (x, y, rx, ry) in ((4, 6, 3, 2), (9, 5, 3.5, 2.5), (12, 7, 2.5, 1.8), (7, 8, 2.5, 1.5))]; c.put(3, 5, pb[2]); c.put(8, 3, pb[2]); c.put(11, 6, pb[2]); c.outline_inside(pb[0])
    d = Canvas(16, 10); d.ellipse(8, 7, 2.5, 1.5, pb[1]); d.put(7, 6, pb[2]); d.outline_inside(pb[0])
    out['stone_pile'] = {'full': S('node_stone_full', c, 8, 9), 'depleted': S('node_stone_dep', d, 8, 9), 'regrow': S('node_stone_dep', d, 8, 9)}
    # mushrooms (brown caps)
    c = Canvas(14, 10); dc = R('dirt')
    for (x, h, r) in ((3, 4, 2), (7, 5, 3), (11, 3, 2)): c.rect(x, 9 - h, 2, h, ss[1]); c.ellipse(x + 0.5, 9 - h - 0.5, r, 1.6, dc[4]); c.put(x, 9 - h - 1, dc[5]); c.put(x + 1, 9 - h + 1, dc[2])
    c.outline_inside(dc[1])
    d = Canvas(14, 10); d.put(4, 8, ss[0]); d.put(8, 8, ss[0]); d.put(9, 8, ss[0])
    rg = Canvas(14, 10); rg.rect(7, 7, 2, 2, ss[1]); rg.ellipse(7.5, 6.5, 1.5, 1, dc[4]); rg.outline_inside(dc[1])
    out['mushroom'] = {'full': S('node_mush_full', c, 7, 9), 'depleted': S('node_mush_dep', d, 7, 9), 'regrow': S('node_mush_regrow', rg, 7, 9)}
    # flowers (three colours)
    for kind, fam in (('flower_w', fw), ('flower_b', fb), ('flower_r', br)):
        c = Canvas(16, 12)
        for i, x in enumerate((3, 7, 11)):
            top = 3 + (i % 2); c.vline(x, top + 1, 11, g[2]); c.put(x + 1, 9, g[3]); c.put(x, top, fam[1]); c.put(x - 1, top, fam[1]); c.put(x + 1, top, fam[0]); c.put(x, top - 1, fam[2]); c.put(x, top + 1, fam[0])
            if kind == 'flower_w': c.put(x, top, R('flower_y')[1])
        d = Canvas(16, 12); [d.vline(x, 8, 11, g[2]) for x in (3, 7, 11)]
        rg = Canvas(16, 12); [rg.vline(x, 7, 11, g[2]) for x in (3, 7, 11)]; rg.put(7, 6, fam[0])
        out[kind] = {'full': S(f'node_{kind}_full', c, 8, 11), 'depleted': S(f'node_{kind}_dep', d, 8, 11), 'regrow': S(f'node_{kind}_regrow', rg, 8, 11)}
    # berry bush (blackberry) / rowan berries marker
    base = shrub(2).c
    c = base.copy(); rng = random.Random(7)
    for _ in range(9):
        x, y = rng.randint(6, 22), rng.randint(6, 16)
        if c.a[y, x] != 0: c.put(x, y, R('flower_p')[0]); c.put(x + 1, y, R('flower_p')[1])
    out['berry_bush'] = {'full': S('node_berry_full', c, 14, 20), 'depleted': S('node_berry_dep', base.copy(), 14, 20), 'regrow': S('node_berry_dep', base.copy(), 14, 20)}
    c = Canvas(16, 10)
    for (x, y) in ((4, 4), (8, 3), (12, 5), (6, 7), (10, 7)): c.put(x, y, br[1]); c.put(x + 1, y, br[0]); c.put(x, y - 1, br[2])
    out['berry_rowan'] = {'full': S('node_rowan_full', c, 8, 8), 'depleted': S('node_rowan_dep', Canvas(16, 10), 8, 8), 'regrow': S('node_rowan_dep', Canvas(16, 10), 8, 8)}
    # herb clump (mint / reed fibre) and vines
    c = Canvas(14, 12)
    for i in range(6): x = 2 + i * 2; h = 5 + (i % 3) * 2; c.vline(x, 11 - h, 11, mo[1] if i % 2 else mo[2]); c.put(x, 11 - h, mo[3]); c.put(x + 1, 11 - h + 2, mo[0])
    d = Canvas(14, 12); [d.vline(2 + i * 2, 9, 11, mo[1]) for i in range(6)]
    out['herb'] = {'full': S('node_herb_full', c, 7, 11), 'depleted': S('node_herb_dep', d, 7, 11), 'regrow': S('node_herb_dep', d, 7, 11)}
    c = Canvas(14, 22); rng = random.Random(3)
    for sx in (3, 7, 11):
        x, y = sx, 20
        for i in range(16): x += rng.choice((-1, 0, 0, 1)); y -= 1; c.put(max(0, min(13, x)), y, mo[1]); 
        c.put(sx, 20, mo[0])
    for _ in range(10): c.put(rng.randint(1, 12), rng.randint(2, 18), mo[2])
    d = Canvas(14, 22); d.vline(7, 14, 20, mo[0]); d.put(6, 19, mo[1])
    out['vine'] = {'full': S('node_vine_full', c, 7, 20), 'depleted': S('node_vine_dep', d, 7, 20), 'regrow': S('node_vine_dep', d, 7, 20)}
    # moss pad
    c = Canvas(14, 8); c.ellipse(7, 5, 6, 2.5, mo[1]); c.ellipse(5, 4, 3, 1.5, mo[2]); c.put(10, 6, mo[0]); c.outline_inside(mo[0])
    d = Canvas(14, 8); d.ellipse(7, 5, 3, 1.5, mo[0])
    out['moss_pad'] = {'full': S('node_moss_full', c, 7, 7), 'depleted': S('node_moss_dep', d, 7, 7), 'regrow': S('node_moss_dep', d, 7, 7)}
    # tree marker (invisible: the oak itself is the visual; depleted shows chop marks at the base)
    e = Canvas(2, 2); d = Canvas(14, 8); d.hline(3, 10, 4, w[4]); d.hline(4, 9, 5, w[3]); d.put(5, 3, w[4]); d.put(8, 3, w[4])
    out['tree_marker'] = {'full': S('node_tree_full', e, 1, 1), 'depleted': S('node_tree_dep', d, 7, 7), 'regrow': S('node_tree_dep', d, 7, 7)}
    # mineral deposit: full (ore flecks) / damaged / depleted
    def deposit(stage):
        c = Canvas(26, 18); shaded_blob(c, 13, 11, 11, 6, st, light=(-0.4, -0.5), ranks=(1, 2, 3, 4)); shaded_blob(c, 17, 7, 6, 5, st, light=(-0.4, -0.5), ranks=(1, 2, 3, 4))
        m = _mask_of(c, ['stone']); rng = random.Random(11)
        flecks = [(8, 10), (12, 8), (16, 12), (19, 9), (10, 14), (14, 13), (21, 13)][: (7 if stage == 'full' else 3 if stage == 'regrow' else 0)]
        for (x, y) in flecks: c.put(x, y, mo[2]); c.put(x + 1, y, mo[1]); c.put(x, y + 1, R('flower_w')[2] if (x + y) % 3 == 0 else mo[1])
        if stage != 'full':
            for (x, y) in ((6, 9), (13, 6), (18, 12), (9, 13)): c.put(x, y, st[0]); c.put(x + 1, y + 1, st[1]); c.put(x + 2, y, st[0])
            if stage == 'depleted': c.rect(10, 12, 7, 4, st[1]); c.put(11, 13, st[0]); c.put(15, 14, st[0])
        c.outline_inside(st[0], mask=m); return c
    out['deposit'] = {'full': S('node_deposit_full', deposit('full'), 13, 17, ('solid',)), 'depleted': S('node_deposit_dep', deposit('depleted'), 13, 17, ('solid',)), 'regrow': S('node_deposit_regrow', deposit('regrow'), 13, 17, ('solid',))}
    # scrap pile / hidden / clay / feather
    c = Canvas(18, 10); c.poly([(2, 7), (9, 3), (14, 5), (8, 9)], mr[1]); c.line(3, 7, 8, 4, mr[2]); c.rect(10, 6, 5, 3, mt[2]); c.put(10, 6, mt[3]); c.put(5, 8, mt[1]); c.put(13, 3, mt[2]); c.put(14, 3, mt[2]); c.outline_inside(mt[0])
    d = Canvas(18, 10); d.rect(7, 7, 4, 2, mt[1]); d.put(7, 7, mt[2]); d.outline_inside(mt[0])
    out['scrap_pile'] = {'full': S('node_scrap_full', c, 9, 9), 'depleted': S('node_scrap_dep', d, 9, 9), 'regrow': S('node_scrap_dep', d, 9, 9)}
    out['hidden'] = {'full': S('node_hidden', Canvas(2, 2), 1, 1), 'depleted': S('node_hidden', Canvas(2, 2), 1, 1), 'regrow': S('node_hidden', Canvas(2, 2), 1, 1)}
    c = Canvas(16, 8); md = R('mud'); c.ellipse(8, 5, 7, 2.5, md[2]); c.ellipse(6, 4, 3, 1.2, md[3]); c.put(11, 6, md[1]); c.outline_inside(md[0])
    d = Canvas(16, 8); d.ellipse(8, 5, 7, 2.5, md[1]); d.ellipse(8, 5, 3, 1.3, md[0]); d.outline_inside(md[0])
    out['clay'] = {'full': S('node_clay_full', c, 8, 7), 'depleted': S('node_clay_dep', d, 8, 7), 'regrow': S('node_clay_dep', d, 8, 7)}
    c = Canvas(10, 8); c.line(1, 6, 7, 1, st[3]); c.poly([(2, 6), (7, 1), (8, 3), (5, 6)], st[4]); c.line(2, 6, 6, 2, st[2])
    out['feather'] = {'full': S('node_feather_full', c, 5, 7), 'depleted': S('node_feather_dep', Canvas(2, 2), 1, 1), 'regrow': S('node_feather_dep', Canvas(2, 2), 1, 1)}
    # nocturnal: glow caps with moondew beads, ghostcap, night lily, lantern moth
    gc = mushrooms(0, glow=True).c.copy()
    for (x, y) in ((3, 4), (8, 3), (11, 5)): gc.put(x, y, R('moonlight')[2])
    out['glowcap'] = {'full': S('node_glowcap_full', gc, 7, 9), 'depleted': S('node_glowcap_dep', mushrooms(0, glow=True).c.copy(), 7, 9), 'regrow': S('node_glowcap_dep', mushrooms(0, glow=True).c.copy(), 7, 9)}
    c = Canvas(12, 14); c.rect(5, 6, 2, 7, mi[2]); c.put(5, 6, mi[1]); c.ellipse(6, 5, 4.5, 3, mi[2]); c.ellipse(5, 4, 2.5, 1.5, R('moonlight')[2]); c.put(3, 7, mi[1]); c.put(9, 7, mi[1]); c.outline_inside(mi[0])
    out['ghostcap'] = {'full': S('node_ghostcap_full', c, 6, 13), 'depleted': S('node_ghostcap_dep', Canvas(2, 2), 1, 1), 'regrow': S('node_ghostcap_dep', Canvas(2, 2), 1, 1)}
    c = Canvas(14, 10); li = R('lily'); c.ellipse(7, 6, 6, 3, li[2]); c.put(11, 7, li[1]); c.put(6, 8, li[1])
    for dx, dy in ((0, -2), (-2, 0), (2, 0), (0, 1)): c.put(6 + dx, 4 + dy, mi[2])
    c.put(6, 4, R('moonlight')[2]); c.put(5, 3, R('moonlight')[1]); c.put(7, 3, R('moonlight')[1])
    d = lily_pad(1).c.copy()
    out['nightlily'] = {'full': S('node_nightlily_full', c, 7, 8), 'depleted': S('node_nightlily_dep', d, 5, 6), 'regrow': S('node_nightlily_dep', d, 5, 6)}
    c = Canvas(12, 8); c.poly([(1, 2), (6, 4), (1, 7)], mi[2]); c.poly([(11, 2), (6, 4), (11, 7)], mi[2]); c.rect(5, 2, 2, 5, mi[1]); c.put(3, 4, R('moonlight')[2]); c.put(9, 4, R('moonlight')[2]); c.put(5, 1, mi[0]); c.put(7, 1, mi[0])
    out['moth'] = {'full': S('node_moth_full', c, 6, 7), 'depleted': S('node_moth_dep', Canvas(2, 2), 1, 1), 'regrow': S('node_moth_dep', Canvas(2, 2), 1, 1)}
    return out
