"""Trees, grown rather than stamped: every tree is a branch skeleton first (trunk, limbs, twigs), then leaves.

The same skeleton draws the leafy tree (spring, summer, autumn through the palette) and the bare winter tree, so a
tree keeps its identity across the year: the oak by the tent has the same lean and the same forked limb in January.

Species have their own silhouettes, not recolours:
  oak     a broad, lumpy dome of big leaf clumps on a stout trunk with root flare; limbs show through gaps
  birch   slender white trunk with dark lenticels, an airy narrow crown of small drooping clumps
  willow  short thick trunk, a dome that falls in long curtains of hanging strands
  snag    a dead tree: bark gone silver, broken limbs, no leaves

Shading everywhere: light from the upper left; each leaf clump has its own lit top and shaded lower rim (layered
foliage), the crown has a darker underside, the outline is the darkest tone of the material, lightened on the lit edge.
"""
from __future__ import annotations
import math, random
import numpy as np
from .canvas import Canvas
from .palette import PAL
from .noise import value_noise
from .camp_art import lit_blob, sel_outline, _sprite

R = PAL.ramp


# ---------------------------------------------------------------------------------------------------------------- skeleton
class Skeleton:
    def __init__(self):
        self.segs = []          # (x0, y0, x1, y1, w0, w1, depth)
        self.tips = []          # (x, y, depth, angle)

def grow(sk, x, y, ang, length, width, depth, rng, sp):
    """Grow a limb from (x, y) at angle ang (0 = up) and branch at its end."""
    x1 = x + math.sin(ang) * length; y1 = y - math.cos(ang) * length
    w1 = max(0.6, width * sp['taper'])
    sk.segs.append((x, y, x1, y1, width, w1, depth))
    if depth >= sp['depth'] or length < 2.5:
        sk.tips.append((x1, y1, depth, ang)); return
    n = 2 if rng.random() < sp['fork2'] else 3
    spread = sp['spread']
    for k in range(n):
        a = ang + (k - (n - 1) / 2) * spread + rng.uniform(-0.18, 0.18)
        a += (sp['droop'] * (1 if a > 0 else -1)) * depth * 0.25
        grow(sk, x1, y1, a, length * rng.uniform(*sp['shrink']), w1 * 0.8, depth + 1, rng, sp)
    if rng.random() < 0.5: sk.tips.append((x1, y1, depth, ang))


def fit(sk, cx, base, W, margin, top_room=3):
    """Scale the grown skeleton about the trunk base so the crown (tips plus leaf radius) fits the canvas."""
    xs = [s_[2] for s_ in sk.segs] + [t[0] for t in sk.tips]; ys = [s_[3] for s_ in sk.segs] + [t[1] for t in sk.tips]
    sy = (base - top_room - margin) / max(1, base - min(ys)); sx = (W / 2 - 2 - margin) / max(1, max(abs(x - cx) for x in xs))
    k = min(1.0, sy, sx)
    if k >= 1.0: return
    tr = lambda x, y: (cx + (x - cx) * k, base + (y - base) * k)
    sk.segs = [(*tr(a, b), *tr(c_, d), w0, w1, dd) for (a, b, c_, d, w0, w1, dd) in sk.segs]
    sk.tips = [(*tr(x, y), d, a) for (x, y, d, a) in sk.tips]


def draw_wood(c, sk, ramp, birch=False, max_depth=99, seed=0):
    """Paint the skeleton as rounded limbs: lit left edge, mid, shaded right edge, thinning to 1 px twigs."""
    for (x0, y0, x1, y1, w0, w1, d) in sorted(sk.segs, key=lambda s: s[6]):
        if d > max_depth: continue
        L = max(1, int(math.hypot(x1 - x0, y1 - y0) * 2))
        for i in range(L + 1):
            t = i / L; x = x0 + (x1 - x0) * t; y = y0 + (y1 - y0) * t; w = w0 + (w1 - w0) * t
            hw = w / 2
            for dx in range(int(math.floor(x - hw)), int(math.ceil(x + hw)) + 1):
                u = (dx + 0.5 - x) / max(0.5, hw)
                if abs(u) > 1.05: continue
                tone = 3 if u < -0.35 else 2 if u < 0.4 else 1
                if w < 1.6: tone = 2 if d < 3 else 1
                if birch and w >= 2 and value_noise(dx, int(y), 2.0, seed) > 0.78 and abs(u) < 0.8: tone = 0     # lenticels
                c.put(dx, int(round(y)), ramp[tone])


# ---------------------------------------------------------------------------------------------------------------- foliage
def clump_crown(c, sk, ramp, rng, size, cx, cy, crx, cry, n_extra=6, lo=1, hi=4, seed=0):
    """Leaf clumps at the limb tips plus a few inside the crown, painted back to front, each with its own shaded
    lower rim; then a dark underside across the crown and a selective outline."""
    clumps = [(x, y, size * rng.uniform(0.8, 1.15), size * 0.78 * rng.uniform(0.85, 1.1)) for (x, y, d, a) in sk.tips]
    for (x0, y0, x1, y1, w0, w1, d) in sk.segs:                     # leaves also clothe the limbs, not only their tips
        if d >= 1:
            for t in (0.45, 0.8):
                clumps.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, size * 0.85, size * 0.68))
    for k in range(n_extra):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0, 0.55)
        clumps.append((cx + math.cos(a) * crx * r, cy + math.sin(a) * cry * r, size * 1.1, size * 0.85))
    layer = Canvas(c.w, c.h)
    for (x, y, rx, ry) in sorted(clumps, key=lambda q: q[1] + q[0] * 0.15):
        m = lit_blob(layer, x, y, rx, ry, ramp, seed=int(x * 17 + y * 5) + seed, rough=0.45, lo=lo + 1, hi=hi if y < cy + cry * 0.2 else hi - 1, outline=False)
        p = np.pad(m, 1); rim = m & (~p[2:, 1:-1] | ~p[1:-1, 2:])
        layer.a[rim] = ramp[lo]
    m = layer.a != 0
    under = m & (np.arange(c.h)[:, None] > cy + cry * 0.45) & (layer.a != ramp[lo])
    layer.a[under & (layer.a > ramp[lo + 1])] = ramp[lo + 1]
    sel_outline(layer, m, ramp)
    return layer, m


def _finish(c, wood_ramp, extra_fams=()):
    m = c.a != 0; p = np.pad(m, 1)
    edge = m & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
    c.a[edge & np.isin(c.a, list(wood_ramp[1:]))] = wood_ramp[0]


def _roots(c, cx, base, tw, ramp, rng):
    for (dx, k) in ((-1, 3), (1, 1)):
        L = rng.randint(3, 5)
        for i in range(L):
            x = int(cx + dx * (tw / 2 + i)); y = base - (1 if i < L - 2 else 0)
            c.put(x, y, ramp[k]); c.put(x, y + 1, ramp[0])


SPECIES = {
    'oak': dict(depth=3, fork2=0.55, spread=0.62, droop=0.10, taper=0.62, shrink=(0.62, 0.78), wood='wood', leaves='oak'),
    'birch': dict(depth=3, fork2=0.75, spread=0.38, droop=0.22, taper=0.6, shrink=(0.6, 0.75), wood='bark_birch', leaves='birch'),
    'willow': dict(depth=3, fork2=0.5, spread=0.85, droop=0.35, taper=0.6, shrink=(0.55, 0.72), wood='wood', leaves='birch'),
    'snag': dict(depth=2, fork2=0.8, spread=0.7, droop=0.05, taper=0.55, shrink=(0.45, 0.7), wood='wood_grey', leaves=None),
}


def leaf_clump(layer, x, y, rx, ry, ramp, seed, back=False):
    """One big clump of leaves, painted the way foliage is painted in pixel art: a mid-tone mass, a shaded crescent
    on the lower right, a dark rim underneath, a lit crescent on the upper left, and leaf marks (little lit
    flicks in the light, dark nicks in the shade) instead of noise."""
    H, W = layer.h, layer.w; m = np.zeros((H, W), bool)
    b = 0 if not back else -1
    for yy in range(max(0, int(y - ry - 2)), min(H, int(y + ry + 3))):
        for xx in range(max(0, int(x - rx - 2)), min(W, int(x + rx + 3))):
            u = (xx + .5 - x) / rx; v = (yy + .5 - y) / ry
            r2 = u * u + v * v + (value_noise(xx, yy, 2.5, seed) - .5) * 0.38
            if r2 > 1: continue
            t = 3
            if v > 0.25 or (u > 0.45 and v > -0.2): t = 2
            if v > 0.72 or (u > 0.75 and v > 0.2): t = 1
            if u + v * 1.2 < -0.55 and r2 < 0.85: t = 4
            layer.a[yy, xx] = ramp[max(1, t + b)]; m[yy, xx] = True
    # leaf marks
    rng = random.Random(seed)
    for k in range(int(rx * ry / 13)):
        xx = int(x + rng.uniform(-rx, rx) * 0.85); yy = int(y + rng.uniform(-ry, ry) * 0.85)
        if not (0 <= xx < W - 1 and 0 <= yy < H) or not m[yy, xx]: continue
        cur = layer.a[yy, xx]
        if cur == ramp[4 + b] if 4 + b <= 5 else False:
            layer.a[yy, xx] = ramp[min(5, 5 + b)]; 
            if m[yy, xx + 1]: layer.a[yy, xx + 1] = ramp[min(5, 5 + b)] if rng.random() < 0.4 else cur
        elif cur == ramp[3 + b]:
            if rng.random() < 0.5: layer.a[yy, xx] = ramp[4 + b]
            else: layer.a[yy, xx] = ramp[2 + b]
        elif cur == ramp[2 + b] and rng.random() < 0.6: layer.a[yy, xx] = ramp[1]
    p = np.pad(m, 1); rim = m & (~p[2:, 1:-1])
    layer.a[rim] = ramp[1]
    return m


LAYOUTS = {   # crown clumps relative to the crown box (u, v in -1..1, size factor); back row first
    'oak': [(-0.55, -0.55, 0.75), (0.1, -0.75, 0.8), (0.6, -0.45, 0.72), (-0.85, 0.05, 0.7), (-0.25, -0.15, 0.95), (0.45, 0.05, 0.85),
            (0.85, 0.25, 0.62), (-0.5, 0.5, 0.8), (0.15, 0.55, 0.88)],
    'birch': [(-0.1, -0.9, 0.62), (0.4, -0.7, 0.66), (-0.5, -0.55, 0.68), (0.05, -0.45, 0.8), (0.6, -0.2, 0.62), (-0.6, -0.1, 0.66), (0.2, 0.0, 0.8),
              (-0.3, 0.25, 0.75), (0.55, 0.35, 0.6), (-0.55, 0.5, 0.58), (0.1, 0.55, 0.7), (-0.1, 0.85, 0.5)],
    'willow': [(-0.5, -0.6, 0.7), (0.3, -0.7, 0.72), (-0.85, -0.05, 0.62), (0.0, -0.15, 0.85), (0.8, -0.05, 0.62), (-0.45, 0.35, 0.7), (0.45, 0.35, 0.7)],
}


def tree(species, name, seed, W=58, H=70, lean=0.0, bare=False):
    """Grow and paint one tree: crown clumps are laid out first, then the limbs are grown to reach them, so the
    bare winter tree is the same tree with its leaves gone."""
    sp = SPECIES[species]; rng = random.Random(seed)
    c = Canvas(W, H); wd = R(sp['wood'])
    cx, base = W // 2 + int(lean * 3), H - 3
    if species == 'snag':
        sk = Skeleton(); grow(sk, cx, base, lean * 0.2, H * 0.42, 5.0, 0, rng, sp); fit(sk, cx, base, W, 2)
        draw_wood(c, sk, wd, seed=seed); _roots(c, cx, base, 5, wd, rng); _finish(c, wd)
        return _sprite(name, c, cx, base + 1, shadow=(max(8, int(W * 0.3)), 3, 5, -1), soft_shadow=True, tags=('tree', 'ysort'), contact=(4, 1.4))
    # crown box and trunk
    if species == 'oak':
        tw = rng.uniform(6.5, 8.0); ctop, cbot = 2, H * rng.uniform(0.76, 0.80); crx = W / 2 - 3; csize = W * 0.215
    elif species == 'birch':
        tw = rng.uniform(2.8, 3.4); ctop, cbot = 3, H * 0.74; crx = W / 2 - 3; csize = W * 0.21
    else:
        tw = 7.0; ctop, cbot = 3, H * 0.52; crx = W / 2 - 4; csize = W * 0.16
    ccx = cx + lean * 4; ccy = (ctop + cbot) / 2; cry = (cbot - ctop) / 2
    lay = [(ccx + u * crx * 0.80 + u * abs(u) * lean * 3 + rng.uniform(-1.5, 1.5), ccy + v * cry * 0.82 + rng.uniform(-1, 1), csize * f * rng.uniform(0.9, 1.12)) for (u, v, f) in LAYOUTS[species]]
    if rng.random() < 0.5: lay = [(2 * ccx - x, y, r) for (x, y, r) in lay]          # mirror for variety
    if species == 'oak':                                                          # each oak its own outline: a missing lobe here, an extra one there
        drop = rng.choice([0, 2, 3, 6]); lay = lay[:drop] + lay[drop + 1:]        # only rim lobes go missing, never the heart
        a = rng.uniform(-math.pi, 0); lay.insert(rng.randrange(3), (ccx + math.cos(a) * crx * 0.85, ccy + math.sin(a) * cry * 0.75, csize * 0.7))
    # the skeleton: the trunk rises to a fork; a limb reaches each clump (it forks once on the way)
    sk = Skeleton(); fork_y = cbot - cry * (0.35 if species != 'birch' else 0.9)
    sk.segs.append((cx, base, ccx, fork_y, tw, tw * 0.72, 0))
    sk.segs.append((cx, base, cx, base - 4, tw * 1.45, tw, 0))                     # the flare where the trunk meets its roots
    for (x, y, r) in lay:
        mx, my = (ccx + x) / 2 + rng.uniform(-2, 2), (fork_y + y) / 2
        w0 = tw * 0.55 if species != 'birch' else tw * 0.5
        sk.segs.append((ccx, fork_y, mx, my, w0, w0 * 0.7, 1)); sk.segs.append((mx, my, x, y, w0 * 0.7, 0.8, 2))
        for k in range(2):                                                         # twigs: what a bare tree is made of
            a = math.atan2(x - mx, -(y - my)) + rng.uniform(-0.8, 0.8); L = r * rng.uniform(0.5, 0.9)
            sk.segs.append((x, y, x + math.sin(a) * L, y - math.cos(a) * L, 0.8, 0.6, 3))
        sk.tips.append((x, y, 2, 0))
    if bare:
        draw_wood(c, sk, wd, birch=species == 'birch', seed=seed)
    else:
        draw_wood(c, sk, wd, birch=species == 'birch', max_depth=1, seed=seed)
    _roots(c, cx, base, tw, wd, rng)
    if not bare:
        lv = R(sp['leaves']); layer = Canvas(W, H); m = np.zeros((H, W), bool)
        n_back = 3
        for i, (x, y, r) in enumerate(lay):
            m |= leaf_clump(layer, x, y, r, r * 0.8, lv, seed + i * 7, back=i < n_back)
        if species == 'willow':                                                    # the curtains
            bot = {}
            ys_, xs_ = np.nonzero(m)
            for k in range(len(xs_)): bot[xs_[k]] = max(bot.get(xs_[k], 0), ys_[k])
            for x, yb in bot.items():
                if (x * 7 + seed) % 5 == 0: continue                                    # a few gaps let the trunk show
                L = int(5 + value_noise(int(x), 0, 2.0, seed) * 14 + (x % 3))
                for y in range(yb - 2, min(H - 5, yb + L)):
                    k = (y - yb) / max(1, L)
                    layer.a[y, x] = (lv[3] if x % 2 else lv[2]) if k < 0.35 else (lv[2] if x % 2 else lv[1]); m[y, x] = True
                if yb + L < H - 5: layer.a[yb + L, x] = lv[4] if x % 2 else lv[3]; m[yb + L, x] = True
        sel_outline(layer, m, lv)
        c.a[m] = layer.a[m]
    _finish(c, wd)
    tags = ('tree', 'ysort') + (('winter',) if bare else ())
    return _sprite(name, c, cx, base + 1, shadow=(max(9, int(W * 0.40)), 4, 6, -1), soft_shadow=True, tags=tags, contact=(tw * 0.9, 1.6))


# ---------------------------------------------------------------------------------------------------------------- the set
TREES = [  # name, species, seed, W, H, lean
    ('oak_0', 'oak', 11, 58, 70, 0.0), ('oak_1', 'oak', 23, 60, 66, -0.3), ('oak_2', 'oak', 37, 52, 72, 0.2), ('oak_3', 'oak', 41, 62, 64, 0.5),
    ('birch_0', 'birch', 5, 34, 66, 0.1), ('birch_1', 'birch', 9, 30, 60, -0.2),
    ('willow_0', 'willow', 3, 64, 62, 0.0), ('willow_1', 'willow', 8, 56, 58, 0.2),
    ('dead_0', 'snag', 4, 40, 58, 0.3),
]


def add_trees(lib):
    for (nm, seed, W, H) in (('rowan_0', 5, 36, 44), ('rowan_1', 9, 30, 40)):       # the meadow rowans stand bare in winter too
        lib[nm + '_winter'] = tree('oak', nm + '_winter', seed, W, H, 0.0, bare=True)
    for (nm, spc, seed, W, H, lean) in TREES:
        lib[nm] = tree(spc, nm, seed, W, H, lean)
        if spc != 'snag':
            bare = tree(spc, nm + '_winter', seed, W, H, lean, bare=True)
            lib[nm + '_winter'] = bare
    return lib
