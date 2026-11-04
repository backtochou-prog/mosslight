"""Hand-authored ground detail, painted across the whole scene after the tile pass.

The dual-grid tiles give every material its shape and edges; this pass gives the surfaces their craft, the way an
artist paints over a block-in. Patterns come from a few authored micro-stamps placed on a jittered grid and steered by
large, smooth noise fields, so nothing repeats at the 16 px tile period and nothing is random single-pixel pepper.

  grass_pass   blade clumps in three close tones, sun drifts, darker growth at the feet of things
  path_pass    trodden dirt: a lighter worn centre, darker ruts at the sides, pebbles, grass creeping in at the edge
  camp_ground  packed earth around the fire and the tent: footprints, ash, a few stubborn grass islands
"""
from __future__ import annotations
import math, random
import numpy as np
from .palette import PAL
from .noise import fbm, value_noise

G = PAL.ramp('grass')          # 1..7, base is G[3]
D = PAL.ramp('dirt')
E = PAL.ramp('earth')
PB = PAL.ramp('pebble')
ST = PAL.ramp('stone')

# blade clumps: L = one tone lighter than the ground under them, H = two lighter, D = one darker (the shadow at the root)
CLUMPS = [            # blades: a lit tip (L) over a darker stem (D): the texture reads as depth, not as sparkle
    ["L.L",
     "D.D"],
    [".L.",
     "LD.",
     "D.."],
    ["L..L",
     "D.LD",
     "..D."],
    [".L",
     "LD",
     "D."],
    ["L.L.L",
     "D.D.D"],
    ["..L",
     ".LD",
     "LD.",
     "D.."],
]
SPARSE = [["L", "D"], ["D.D"]]


def _grid_points(W, H, cw, ch, seed, jitter=1.0):
    rng = random.Random(seed)
    for gy in range(0, H, ch):
        for gx in range(0, W, cw):
            off = (gy // ch) % 2 * cw // 2                        # brick offset: no visible columns
            yield gx + off + int(rng.random() * cw * jitter), gy + int(rng.random() * ch * jitter), rng


def _stamp(a, ok, x, y, pat, tones):
    """Paint an authored pattern if every pixel it touches is allowed. tones maps L/H/D -> palette index."""
    h, w = len(pat), len(pat[0]); H, W = a.shape
    if x < 0 or y < 0 or x + w > W or y + h > H: return False
    sub = ok[y:y + h, x:x + w]
    for yy, row in enumerate(pat):
        for xx, ch in enumerate(row):
            if ch != '.' and not sub[yy, xx]: return False
    for yy, row in enumerate(pat):
        for xx, ch in enumerate(row):
            if ch != '.': a[y + yy, x + xx] = tones[ch]
    return True


def _erode(m, k=1):
    for _ in range(k):
        p = np.pad(m, 1)
        m = m & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return m


def grass_pass(c, seed=7, shade_near=None):
    """Repaint lush grass with authored clumps. shade_near: list of (x, y, rx, ry) footprints (tree bases, big
    objects) around which the grass grows darker and taller, the way it does in their shade."""
    a = c.a; H, W = a.shape
    W_ = PAL.ramp('worn'); a[np.isin(a, W_)] = G[3]                      # the old lime verge becomes grass
    # the forest floor's tile edge is blocky; within a few pixels of the meadow it becomes shaded grass instead,
    # so the woods' shadow fades into the clearing rather than stopping at a stair-stepped line
    F_ = np.isin(a, PAL.ramp('forest')); gm = np.isin(a, G[1:6])
    near = gm.copy()
    for k in range(4):
        p_ = np.pad(near, 1); near = near | p_[:-2, 1:-1] | p_[2:, 1:-1] | p_[1:-1, :-2] | p_[1:-1, 2:]
    fringe = F_ & near
    yy, xx = np.nonzero(fringe)
    for k in range(len(xx)):
        if value_noise(int(xx[k]), int(yy[k]), 5.0, seed + 40) > 0.3: a[yy[k], xx[k]] = G[2]
    gset = np.isin(a, G[1:6])
    base_ok = np.isin(a, [G[2], G[3], G[4]])
    # 1. the base tone: one calm green, with broad sunlit drifts and a few cool dips (large, clean-edged shapes)
    ys, xs = np.mgrid[0:H, 0:W]
    coarse = np.zeros((H // 4 + 1, W // 4 + 1), np.float32)
    for yy in range(coarse.shape[0]):
        for xx in range(coarse.shape[1]):
            coarse[yy, xx] = fbm(xx * 4, yy * 4, 96.0, seed, 3)
    from PIL import Image as _I
    n = np.array(_I.fromarray(coarse, 'F').resize((coarse.shape[1] * 4, coarse.shape[0] * 4), _I.BILINEAR))[:H, :W]      # smooth, so dips have round edges
    # soften the 4 px blocks into blob edges with a fine wobble so drift outlines are organic, not stair-stepped
    fine = np.zeros((H // 2 + 1, W // 2 + 1), np.float32)
    for yy in range(fine.shape[0]):
        for xx in range(fine.shape[1]):
            fine[yy, xx] = value_noise(xx * 2, yy * 2, 7.0, seed + 3)
    n = n + (np.repeat(np.repeat(fine, 2, 0), 2, 1)[:H, :W] - 0.5) * 0.05
    tone = np.full((H, W), 3, np.int8)
    # (no noise dips: the shade under trees, rocks and the forest wall does that job, with round edges)
    if shade_near:
        for (sx, sy, rx, ry) in shade_near:
            d = ((xs - sx) / rx) ** 2 + ((ys - sy) / ry) ** 2
            tone[(d < 1.0) & (tone > 2)] = 2
    a[base_ok] = np.array(G)[tone[base_ok]]
    # 2. blade clumps on a brick-jittered grid, three tones, never across a material edge
    ok = _erode(gset, 1)
    for x, y, rng in _grid_points(W, H, 7, 6, seed + 11):
        if not (0 <= x < W and 0 <= y < H) or not ok[y, x]: continue
        t = int(tone[y, x])
        v = value_noise(x, y, 18.0, seed + 5)
        if v < 0.22: continue                                       # small open gaps keep it from feeling like wallpaper
        pat = CLUMPS[int(rng.random() * len(CLUMPS))] if v > 0.35 else SPARSE[int(rng.random() * len(SPARSE))]
        sun = fbm(x, y, 80.0, seed + 21, 2) > 0.58
        tones = {'L': G[min(6, t + (2 if sun and rng.random() < 0.3 else 1))], 'H': G[min(6, t + 2)], 'D': G[max(1, t - 1)]}
        _stamp(a, ok, x, y, pat, tones)
    return c


def _dirt_marks(a, inner1, inner3, inner5, seed):
    """Fine trodden texture: pale scuffs and dark specks on a jittered grid, paler toward the walking line,
    darker and grittier toward the edges. Never patches."""
    H, W = a.shape
    DIRT_MARKS = [(["LL"], 0.0), (["L.", ".L"], 0.0), (["d"], 0.4), ([".d", "d."], 0.5), (["LLL"], -0.2), (["dd"], 0.6)]
    for x, y, r_ in _grid_points(W, H, 5, 4, seed + 1):
        if not (0 <= x < W and 0 <= y < H) or not inner1[y, x]: continue
        edgey = 0.0 if inner5[y, x] else (0.5 if inner3[y, x] else 1.0)
        if r_.random() < 0.25: continue
        dark = r_.random() < 0.35 + edgey * 0.4
        cands = [p_ for (p_, bias) in DIRT_MARKS if (bias >= 0.4) == dark]
        pat = cands[int(r_.random() * len(cands))]
        _stamp(a, inner1 & np.isin(a, [D[2], D[3], D[4]]), x, y, pat, {'L': D[4], 'd': D[2]})


def path_pass(c, seed=19):
    """Trodden dirt: a lighter, smoother centre line where feet go, darker ruts toward the sides, pebbles that
    gather at the margins, and grass blades leaning in over the edge."""
    a = c.a; H, W = a.shape
    dset = np.isin(a, D[1:6])
    inner1 = _erode(dset, 1); inner3 = _erode(dset, 3); inner5 = _erode(dset, 5)
    rng = random.Random(seed)
    # 1. base tones by depth into the path: rim stays, a soft rut band, a lighter worn centre
    band = dset & ~inner3 & inner1
    pd = np.pad(dset, 1); near = pd[:-2, 1:-1] | pd[2:, 1:-1] | pd[1:-1, :-2] | pd[1:-1, 2:]
    stray = np.isin(a, PB) & near & ~_erode(np.isin(a, PB), 1); a[stray] = D[3]; dset = dset | stray      # lone tile pebble pixels
    inner1 = _erode(dset, 1); inner3 = _erode(dset, 3); inner5 = _erode(dset, 5); band = dset & ~inner3 & inner1
    plain = np.isin(a, [D[2], D[3], D[4]])
    a[inner1 & plain] = D[3]
    _dirt_marks(a, inner1, inner3, inner5, seed)
    # 2. pebbles: small, lit on top, shaded below; more of them at the margins than in the middle
    def pebble(x, y, big):
        S_ = (E[4], E[3], E[1])                                    # warm grey-brown stones, the colour of the path's own grit
        pts = ([(0, 0, S_[0]), (1, 0, S_[1]), (0, 1, S_[1]), (1, 1, S_[2])] if not big else
               [(1, 0, S_[0]), (2, 0, S_[1]), (0, 1, S_[0]), (1, 1, S_[1]), (2, 1, S_[1]), (3, 1, S_[2]), (1, 2, S_[2]), (2, 2, S_[2])])
        if all(0 <= x + dx < W and 0 <= y + dy < H and inner1[y + dy, x + dx] for dx, dy, _ in pts):
            for dx, dy, col in pts: a[y + dy, x + dx] = col
            if y + 3 < H and inner1[y + 2 + (1 if big else 0), x + 1]: a[y + 2 + (1 if big else 0), x + 1] = D[2]
    for x, y, r_ in _grid_points(W, H, 11, 9, seed + 4):
        if not (0 <= x < W and 0 <= y < H) or not inner1[y, x]: continue
        edge = not inner5[y, x]
        if r_.random() < (0.16 if edge else 0.03): pebble(x, y, r_.random() < 0.35)
    # 3. grass leans in over the edge: blades from the grass side, a dark tip of shadow under them
    gset = np.isin(a, G[2:6])
    up = np.zeros_like(dset); up[1:, :] = dset[1:, :] & gset[:-1, :]          # dirt pixel with grass above
    dn = np.zeros_like(dset); dn[:-1, :] = dset[:-1, :] & gset[1:, :]          # dirt pixel with grass below
    ys, xs = np.nonzero(up)
    for k in range(len(xs)):
        x, y = int(xs[k]), int(ys[k])
        r = value_noise(x, y, 3.0, seed + 7)
        if r > 0.55:
            a[y, x] = G[3]
            if r > 0.7 and y + 1 < H and dset[y + 1, x]: a[y + 1, x] = G[2]
            if y + 2 < H and dset[y + 2, x] and a[y + 2, x] in (D[2], D[3], D[4]): a[y + 2, x] = D[2]
    ys, xs = np.nonzero(dn)
    for k in range(len(xs)):
        x, y = int(xs[k]), int(ys[k])
        r = value_noise(x, y, 3.0, seed + 9)
        if r > 0.62:
            a[y, x] = G[4]
            if r > 0.75 and y - 1 >= 0 and dset[y - 1, x]: a[y - 1, x] = G[3]
    return c


def camp_ground(cx, cy, rx, ry, seed=5, fire=None, links=()):
    """A decal: bare, trodden ground where people have walked, sat and cooked for a long time, in the same dirt as
    the path so the camp and the path are one surface. The outline is an organic blob; links = extra (x, y, rx, ry)
    lobes (the tent mouth, the woodpile) that join it. Inside, the dirt is smooth with a few pale scuffs; toward the
    rim, grass survives in small islands and leans back in. fire = (x, y, r): an ash apron around the fire pit."""
    def d(c, _rng):
        a = c.a; H, W = a.shape
        rng = random.Random(seed)
        lobes = [(cx, cy, rx, ry)] + list(links)
        x0 = int(min(l[0] - l[2] for l in lobes)) - 4; x1 = int(max(l[0] + l[2] for l in lobes)) + 5
        y0 = int(min(l[1] - l[3] for l in lobes)) - 4; y1 = int(max(l[1] + l[3] for l in lobes)) + 5
        grassish = np.isin(a, list(G[1:6]) + list(PAL.ramp('worn')))
        mask = np.zeros_like(grassish); depth = np.zeros(a.shape, np.float32)
        for y in range(max(0, y0), min(H, y1)):
            for x in range(max(0, x0), min(W, x1)):
                dd = min(math.hypot((x - lx) / lrx, (y - ly) / lry) for (lx, ly, lrx, lry) in lobes)
                dd += (value_noise(x, y, 12.0, seed) - 0.5) * 0.30 + (value_noise(x, y, 5.0, seed + 1) - 0.5) * 0.10
                if dd < 1.0: mask[y, x] = True; depth[y, x] = dd
        mask &= grassish | np.isin(a, D)
        a[mask] = D[3]
        ys, xs = np.nonzero(mask)
        for k in range(len(xs)):
            x, y = int(xs[k]), int(ys[k]); dd = depth[y, x]
            g = value_noise(x, y, 6.0, seed + 3)
            if dd > 0.72 and g > 0.86 - (dd - 0.72) * 1.2: a[y, x] = G[3] if g < 0.93 else G[2]      # stubborn grass islands
        edge_cleanup(c)
        dm = mask & np.isin(a, D)
        _dirt_marks(a, _erode(dm, 1), _erode(dm, 3), _erode(dm, 6), seed + 30)
        # the lip: dirt meeting grass is a shade darker, and blades lean in over it
        p = np.pad(dm, 1)
        lip = dm & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
        a[lip] = D[2]
        up = lip & np.pad(~dm, ((1, 0), (0, 0)))[:-1, :]
        ys, xs = np.nonzero(up)
        for k in range(len(xs)):
            x, y = int(xs[k]), int(ys[k])
            if value_noise(x, y, 3.0, seed + 4) > 0.5:
                a[y, x] = G[3]
                if y + 1 < H and dm[y + 1, x] and rng.random() < 0.5: a[y + 1, x] = G[2]
        # a few small stones kicked to the side
        for _ in range(int(rx * ry / 220)):
            x = int(cx + (rng.random() * 2 - 1) * rx * 0.85); y = int(cy + (rng.random() * 2 - 1) * ry * 0.85)
            if 0 < x < W - 3 and 0 < y < H - 3 and dm[y:y + 2, x:x + 2].all() and depth[y, x] > 0.45:
                a[y, x] = E[4]; a[y, x + 1] = E[3]; a[y + 1, x] = E[3]; a[y + 1, x + 1] = E[1]; a[y + 2, x + 1] = D[2]
        if fire:                                                           # ash and char spread around the pit
            fx, fy, fr = fire
            for y in range(int(fy - fr - 2), int(fy + fr) + 3):
                for x in range(int(fx - fr * 1.7) - 2, int(fx + fr * 1.7) + 3):
                    if not (0 <= x < W and 0 <= y < H) or not dm[y, x]: continue
                    dd = math.hypot((x - fx) / (fr * 1.7), (y - fy) / fr) + (value_noise(x, y, 5.0, seed + 6) - 0.5) * 0.35
                    if dd < 0.8: a[y, x] = E[1] if dd < 0.55 else E[2]
                    elif dd < 1.05: a[y, x] = D[2]
    return d


def forest_depth(seed=13, margin=10):
    """A decal: where the forest floor runs deep (more than `margin` px from the clearing), the gaps between the
    edge trees show the next ranks of canopy instead of bare dark ground: overlapping dark crowns, lit only on their
    upper rims, darker the deeper they sit. Gives the clearing a wall of woods to sit in."""
    from .canvas import Canvas
    def d(c, _rng):
        a = c.a; H, W = a.shape
        F = PAL.ramp('forest'); O = PAL.ramp('oak'); P = PAL.ramp('pine')
        fm = np.isin(a, F) | np.isin(a, PAL.ramp('leaf_litter'))
        deep = _erode(fm, margin)
        rng = random.Random(seed)
        layer = Canvas(W, H)
        pts = sorted(_grid_points(W, H, 16, 11, seed, jitter=1.4), key=lambda q: q[1])
        for x, y, r_ in pts:
            if not (0 <= x < W and 0 <= y < H) or not deep[y, x]: continue
            rx, ry = r_.uniform(11, 16), r_.uniform(8, 11)
            ramp = P if r_.random() < 0.25 else O
            m = np.zeros((H, W), bool)
            y0, y1, x0, x1 = max(0, int(y - ry - 1)), min(H, int(y + ry + 2)), max(0, int(x - rx - 1)), min(W, int(x + rx + 2))
            yy, xx = np.mgrid[y0:y1, x0:x1]
            wob = np.array([[value_noise(int(px_), int(py_), 3.0, seed + 5) for px_ in range(x0, x1)] for py_ in range(y0, y1)])
            inside = ((xx - x) / rx) ** 2 + ((yy - y) / ry) ** 2 + (wob - 0.5) * 0.5 < 1
            m[y0:y1, x0:x1] = inside
            m &= fm
            v = ((yy - y) / ry)
            tone = np.where(v < -0.45, 2, 1)
            sub = layer.a[y0:y1, x0:x1]; mm = m[y0:y1, x0:x1]
            sub[mm] = np.array(ramp)[tone[mm]]
            for k in range(3):                                                  # lit leaf clumps on the crown's upper half
                hx, hy = x + r_.uniform(-0.55, 0.35) * rx, y + r_.uniform(-0.75, -0.2) * ry; hrx, hry = r_.uniform(3, 5), r_.uniform(2, 3.5)
                hm = m & (((np.arange(W)[None, :] - hx) / hrx) ** 2 + ((np.arange(H)[:, None] - hy) / hry) ** 2 < 1)
                layer.a[hm] = ramp[2] if k else ramp[3]
                hp = np.pad(hm, 1); layer.a[hm & ~hp[2:, 1:-1]] = ramp[1]
            p = np.pad(m, 1); rim = m & ~p[2:, 1:-1]
            layer.a[rim] = ramp[0]
        sel = layer.a != 0
        a[sel] = layer.a[sel]
    return d


def edge_cleanup(c, passes=2):
    """Clean material edges the way an artist tidies a block-in: a lone pixel of dirt poking into grass becomes grass,
    a lone notch of grass bitten into dirt becomes dirt. Shapes keep their wobble but lose their pixel crumbs."""
    a = c.a
    dirt = np.isin(a, list(D[1:6]) + list(E))
    gr = np.isin(a, G[1:6])
    for _ in range(passes):
        p = np.pad(dirt, 1)
        n = p[:-2, 1:-1].astype(int) + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]
        crumb = dirt & (n <= 1) & np.pad(gr, 1)[1:-1, 1:-1]
        a[crumb] = G[3]; dirt &= ~crumb
        bite = gr & (n >= 3)
        a[bite] = D[3]; dirt |= bite; gr &= ~bite
    return c
