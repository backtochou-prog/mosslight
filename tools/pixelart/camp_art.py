"""The campsite's hero props, authored at native resolution (no resampling), in one consistent hand:

  * light from the upper left; every form has a lit side, a mid tone, a shaded side and a dark selective outline
    (the outline is the darkest tone of the object's own material, lightened one step on the lit edge);
  * proportions are set against the camper (22 x 36 px, about two tiles tall): a tent you could crawl into,
    a fire ring a stride across, log seats at sitting height;
  * each prop sits on the ground through a soft cast shadow plus a darker contact footprint (Sprite.shadow / contact).

  tent, campfire (burning / embers / unlit), log_seat (two cuts), chop_block (stump with the axe left in it and
  chips at its foot), woodpile (split rounds stacked between stakes), supply_crate (with a kettle and a tin mug),
  boulder families (large / medium / small, plain and mossy) for geological groups.
"""
from __future__ import annotations
import math, random
import numpy as np
from .canvas import Canvas
from .palette import PAL
from .noise import value_noise

R = PAL.ramp


def _sprite(*a, **k):
    from .objects import Sprite
    return Sprite(*a, **k)


# ---------------------------------------------------------------------------------------------------------------- helpers
def lit_blob(c, cx, cy, rx, ry, ramp, seed=0, rough=0.0, flat=0.0, lo=1, hi=None, outline=True, mask_only=False):
    """A rounded, lit form: tone follows a light from the upper left plus a soft dome, posterised into the ramp
    (ranks lo..hi). rough wobbles the silhouette, flat squashes the bottom so stones sit on the ground."""
    hi = len(ramp) - 1 if hi is None else hi
    H, W = c.h, c.w
    m = np.zeros((H, W), bool); tone = np.zeros((H, W), np.int16)
    for y in range(max(0, int(cy - ry - 2)), min(H, int(cy + ry + 3))):
        for x in range(max(0, int(cx - rx - 2)), min(W, int(cx + rx + 3))):
            u = (x + .5 - cx) / rx; v = (y + .5 - cy) / ry
            if flat and v > 0: v = v * (1 + flat)
            r2 = u * u + v * v
            if rough: r2 += (value_noise(x, y, 3.0, seed) - .5) * rough
            if r2 > 1: continue
            dome = math.sqrt(max(0, 1 - min(1, r2)))
            l = -0.55 * u - 0.70 * v + 0.65 * dome
            t = lo + int(round((l + 0.9) / 2.0 * (hi - lo)))
            m[y, x] = True; tone[y, x] = max(lo, min(hi, t))
    if mask_only: return m
    c.a[m] = np.array(ramp)[tone[m]]
    if outline: sel_outline(c, m, ramp)
    return m


def sel_outline(c, m, ramp):
    """Selective outline: the boundary of m in the ramp's darkest tone; on the lit upper/left edge, one step lighter."""
    p = np.pad(m, 1)
    up = m & ~p[:-2, 1:-1]; dn = m & ~p[2:, 1:-1]; lf = m & ~p[1:-1, :-2]; rt = m & ~p[1:-1, 2:]
    c.a[dn | rt] = ramp[0]
    c.a[(up | lf) & ~(dn | rt)] = ramp[1] if len(ramp) > 3 else ramp[0]


def faceted(c, cx, cy, rx, ry, seed=0, lo=1, top_t=4, mossy=False, lit_rim=True):
    """A rock built from planes, the way rocks are painted: a jittered outline, then three or four facets by Voronoi
    (lit top plane, front, shaded right flank, dark foot), a bright lip where the top plane meets the sky, an
    occasional crevice between planes. Returns the mask."""
    st = R('stone'); mo = R('moss'); rng = random.Random(seed); H, W = c.h, c.w
    n = 9; pts = []
    for k in range(n):
        a = k / n * 2 * math.pi + rng.uniform(-0.18, 0.18); rr = rng.uniform(0.84, 1.04) if rx > 5 else rng.uniform(0.92, 1.02)
        x, y = cx + math.cos(a) * rx * rr, cy + math.sin(a) * ry * rr
        pts.append((x, min(y, cy + ry * 0.62)))                               # a flat foot: it sits on the ground
    tmp = Canvas(W, H); tmp.poly(pts, 1); m = tmp.a == 1
    if not m.any(): return m
    fac = [((cx - rx * 0.12 + rng.uniform(-1, 1), cy - ry * 0.55), top_t), ((cx - rx * 0.62, cy + ry * 0.12), top_t - 1),
           ((cx + rx * 0.05, cy + ry * 0.45), top_t - 1 if rng.random() < 0.5 else top_t - 2), ((cx + rx * 0.66, cy - ry * 0.02), top_t - 2)]
    ys, xs = np.nonzero(m); lab = np.zeros(m.shape, np.int8) - 1
    for k in range(len(xs)):
        x, y = xs[k], ys[k]
        best = min(range(len(fac)), key=lambda i: (x - fac[i][0][0]) ** 2 + ((y - fac[i][0][1]) * 1.25) ** 2)
        lab[y, x] = best
        t = fac[best][1]
        if y >= cy + ry * 0.45: t = max(lo, t - 1)                            # the foot is in its own shadow
        c.a[y, x] = st[max(lo, min(5, t))]
    # crevices on some facet borders, lit lip on the top plane's sky edge
    for k in range(len(xs)):
        x, y = int(xs[k]), int(ys[k])
        if x + 1 < W and m[y, x + 1] and lab[y, x + 1] != lab[y, x] and lab[y, x] >= 0 and (x * 7 + y * 3 + seed) % 3 == 0: c.put(x, y, st[max(1, lo)])
    if mossy:
        top = ys.min()
        for k in range(len(xs)):
            x, y = int(xs[k]), int(ys[k])
            if lab[y, x] in (0, 3) and (y - top) < ry * (0.55 + (value_noise(x, y, 4.0, seed + 9) - .5) * 0.6) and x > cx - rx * 0.4:
                c.put(x, y, mo[2] if (y - top) < ry * 0.25 else mo[1])
    p = np.pad(m, 1)
    up = m & ~p[:-2, 1:-1]; dn = m & ~p[2:, 1:-1]; lf = m & ~p[1:-1, :-2]; rt = m & ~p[1:-1, 2:]
    if lit_rim: c.a[up & (lab == 0)] = st[5]
    c.a[(dn | rt)] = st[0]; c.a[(lf) & ~dn] = st[1]
    c.a[up & (lab != 0)] = st[1]
    return m


def mask_of(c, fams):
    return np.isin(c.a, sum([R(f) for f in fams], []))


# ---------------------------------------------------------------------------------------------------------------- tent
def tent(K=1.3):
    """A canvas ridge tent seen front-on and a little from the right: the lit front gable carries the doorway, both
    flaps rolled and tied back; the right roof runs back into the shade. Guy lines to pegs, a patched hem, a ground
    sheet edge, and inside: a bedroll and a folded blanket. About two and a half camper-heights wide."""
    S = lambda v: int(round(v * K))
    W, H = S(70), S(54)
    c = Canvas(W, H); cv = R('canvas'); rp = R('rope'); ti = R('tent_interior'); wd = R('wood'); fb = R('flower_b'); be = R('berry')
    ax, ay = S(27), S(9)                 # front apex
    bx, by = S(44), S(4)                 # back apex (ridge runs back and to the right)
    gl, gr, gy = S(7), S(47), S(47)         # front gable base
    er, ey = S(64), S(40)                # back-right eave corner
    # right roof plane (shade side), then the left eave sliver (lit), then the front gable
    c.poly([(ax, ay), (bx, by), (er, ey), (gr, gy)], cv[2])
    c.poly([(ax, ay), (bx, by), (bx - 3, by + 2), (ax - 1, ay + 1)], cv[3])
    # roof seams follow the slope; a sun-faded band near the ridge
    for k, t in enumerate((0.32, 0.62)):
        x0 = ax + (bx - ax) * 0 + (gr - ax) * t; y0 = ay + (gy - ay) * t
        c.line(int(x0), int(y0), int(x0 + (bx - ax)), int(y0 + (by - ay)), cv[1])
    c.line(ax + 2, ay + 2, bx - 1, by + 2, cv[3])
    c.poly([(ax, ay), (gr, gy), (gl, gy)], cv[4])                                    # front gable, lit
    for y in range(ay, gy + 1):                                                       # light falls off across the gable
        t = (y - ay) / (gy - ay); xl = ax + (gl - ax) * t; xr = ax + (gr - ax) * t
        for x in range(int(xl), int(xr) + 1):
            u = (x - xl) / max(1, xr - xl)
            if c.get(x, y) != cv[4]: continue
            if u < 0.16: c.put(x, y, cv[5])
            elif u > 0.86: c.put(x, y, cv[3])
    # the roof darkens toward the eave where it turns away from the light; the ridge catches a line of light
    for y in range(by, ey + 8):
        for x in range(ax, er + 1):
            if c.get(x, y) != cv[2]: continue
            # distance to the eave line (gr,gy)-(er,ey)
            d = abs((ey - gy) * x - (er - gr) * y + er * gy - ey * gr) / math.hypot(ey - gy, er - gr)
            if d < 3.5 * K: c.put(x, y, cv[1])
    c.line(ax, ay, gl, gy, cv[5]); c.line(ax - 1, ay + 1, gl - 1, gy, cv[5])          # lit edge
    c.line(ax, ay, gr, gy, cv[3])
    # a darker band where the canvas is weathered at the hem
    for x in range(gl, gr + 1):
        for y in (gy - 1, gy - 2):
            if c.get(x, y) in (cv[4], cv[5]): c.put(x, y, cv[3])
    # doorway: dark interior, a bedroll and blanket catching a little light
    dx0, dx1, dtop = S(17), S(37), S(19)
    c.poly([(ax, dtop), (dx1, gy), (dx0, gy)], ti[0])
    c.poly([(ax, dtop + 4), (dx1 - 3, gy), (dx0 + 3, gy)], ti[1])
    c.rect(dx0 + S(4), gy - 4, S(12), 3, fb[1]); c.hline(dx0 + S(4), dx0 + S(4) + S(12) - 1, gy - 4, fb[2]); c.hline(dx0 + S(4), dx0 + S(4) + S(12) - 1, gy - 2, fb[0])   # bedroll
    c.rect(dx0 + S(6), gy - 6, 5, 2, be[1]); c.hline(dx0 + S(6), dx0 + S(6) + 4, gy - 6, be[2])
    c.rect(dx0 + S(12), gy - 6, 3, 2, R('flower_w')[1]); c.put(dx0 + S(12) + 2, gy - 5, R('flower_w')[0])   # a pillow                                                # folded red blanket
    c.put(ax, dtop, ti[0]); c.put(ax, dtop + 1, ti[0])
    # rolled flaps tied back on both sides of the door
    for (x0, y0, x1, y1, side) in ((ax - 1, dtop, dx0 - 1, gy - 1, -1), (ax + 1, dtop, dx1 + 1, gy - 1, 1)):
        c.line(x0, y0, x1, y1, cv[5] if side < 0 else cv[4]); c.line(x0 + side, y0 + 1, x1 + side, y1, cv[4] if side < 0 else cv[3])
        c.line(x0 + 2 * side, y0 + 2, x1 + 2 * side, y1, cv[3] if side < 0 else cv[2]); c.line(x0 + 3 * side, y0 + 4, x1 + 3 * side, y1, cv[2] if side < 0 else cv[1])
        c.line(x0 - side, y0 + 1, x1 - side, y1, ti[1])                               # the shadowed lip of the doorway
        ty = (y0 + y1) // 2 + 3; tx = x0 + (x1 - x0) * (ty - y0) // max(1, (y1 - y0))
        c.put(tx, ty, rp[0]); c.put(tx + side, ty, rp[0]); c.put(tx + 2 * side, ty + 1, rp[1])       # the tie
    # a sewn patch on the shaded roof and one on the gable
    px_, py_ = S(52), S(26); c.rect(px_, py_, 5, 4, cv[3]); c.hline(px_, px_ + 4, py_, cv[4]); c.vline(px_ + 5, py_, py_ + 3, cv[1]); c.put(px_, py_, cv[1]); c.put(px_ + 2, py_ + 2, cv[1])
    qx, qy = S(39), S(37); c.rect(qx, qy, 4, 3, cv[3]); c.put(qx, qy, cv[2]); c.put(qx + 3, qy + 2, cv[2])
    # ground sheet edge and hem shadow
    c.hline(gl - 1, gr + 1, gy + 1, cv[1]); c.hline(gl + 1, gr - 1, gy + 2, cv[0])
    c.line(gr, gy + 1, er, ey + 1, cv[0])
    # poles: the front pole tip above the apex, and the back pole
    c.vline(ax, ay - 4, ay, wd[3]); c.put(ax, ay - 5, wd[4]); c.vline(bx, by - 3, by, wd[2])
    c.outline_inside(cv[0], mask=mask_of(c, ['canvas']))
    c.line(ax, ay, gl, gy, cv[1])                                                     # lit edge stays readable after the outline
    c.line(ax + 1, ay + 1, gl + 1, gy - 1, cv[5])
    # guy lines and pegs
    for (x0, y0, x1, y1) in ((ax - 1, ay + 2, 1, S(44)), (bx + 1, by + 1, W - 2, S(22)), (er, ey, W - 1, S(47))):
        c.line(x0, y0, x1, y1, rp[1])
        c.vline(x1, y1 - 1, y1 + 1, wd[2]); c.put(x1, y1 - 2, wd[4])
    c.line(gl, gy - 1, 2, H - 4, rp[0]); c.vline(2, H - 5, H - 3, wd[2])
    return _sprite('tent', c, ax, gy + 1, shadow=(S(34), 5, S(6), -1), soft_shadow=True, tags=('structure', 'ysort'), contact=(S(26), 2.0))


# ---------------------------------------------------------------------------------------------------------------- campfire
def campfire(state='burning'):
    """A fire ring a stride across: eleven stones of different sizes and tones set by hand (flat ones at the front
    for sitting close, rounder ones at the back), an ash bed, three split logs leaning into a tipi, glowing embers and
    flames with a hot core. Flame pixels are the 'fire' family, so the game makes them flicker through the ramp."""
    W, H = 34, 44
    c = Canvas(W, H); st = R('stone'); em = R('ember'); wd = R('wood'); f = R('fire'); ea = R('earth')
    cx, cy = 17, 35
    ring = [  # (dx, dy, rx, ry, seed): back row first; nine stones, the front ones flatter (people sit close there)
        (-8, -4, 3.0, 2.3, 1), (-1, -6, 3.4, 2.4, 2), (7, -4, 3.0, 2.3, 3),
        (-12, 0, 3.2, 2.6, 4), (12, 0, 3.2, 2.6, 5),
        (-9, 4, 3.6, 2.5, 6), (-2, 6, 4.0, 2.4, 7), (5, 6, 3.6, 2.4, 8), (11, 4, 3.0, 2.4, 9)]
    def stone(dx, dy, rx, ry, sd):
        m = faceted(c, cx + dx, cy + dy, rx, ry, seed=sd * 7, top_t=5 if dy > 0 else 4)
        if state != 'unlit' and dy > 0:                     # firelight on the inner, upper face of the front stones
            ys, xs = np.nonzero(m)
            top = ys.min() if len(ys) else 0
            for k in range(len(xs)):
                if ys[k] == top + 1 and int(xs[k]) == int(cx + dx - (1 if dx > 0 else -1)): c.put(int(xs[k]), int(ys[k]), f[1] if state == 'burning' else st[4])
    # ash bed and the dark ground inside the ring
    c.ellipse(cx, cy, 11.5, 5.6, ea[0]); c.ellipse(cx, cy - 0.5, 9.0, 4.2, em[0]); c.ellipse(cx - 1, cy - 0.5, 6.0, 2.6, st[1]); c.ellipse(cx + 1, cy, 3.0, 1.2, st[2])
    for (dx, dy, rx, ry, sd) in ring[:5]: stone(dx, dy, rx, ry, sd)
    if state != 'unlit':                                    # embers glowing in the ash
        for (x, y) in ((-3, 1), (2, 1), (5, 0), (-5, -1), (0, 2), (-1, 0), (3, -1)): c.put(cx + x, cy + y, f[0] if (x + y) % 2 else f[1])
    # three split logs leaning into a tipi, charred where they meet
    for (x0, y0, x1, y1) in ((-8, 3, -1, -5), (8, 3, 1, -5), (-1, 4, 1, -6)):
        c.line(cx + x0, cy + y0, cx + x1, cy + y1, wd[2]); c.line(cx + x0 + (1 if x0 < 0 else -1 if x0 > 0 else 1), cy + y0, cx + x1 + (1 if x1 <= 0 else 0), cy + y1 + 1, wd[1])
        c.put(cx + x0, cy + y0, wd[4] if x0 < 0 else wd[3])
        c.put(cx + x1, cy + y1, em[1]); c.put(cx + x1 + (1 if x1 <= 0 else -1), cy + y1 + 1, em[0])
    if state == 'burning':
        c.poly([(cx - 1, cy - 15), (cx + 3, cy - 6), (cx + 5, cy - 2), (cx - 5, cy - 2), (cx - 4, cy - 7)], f[0])
        c.poly([(cx + 4, cy - 11), (cx + 6, cy - 4), (cx + 2, cy - 4)], f[0])
        c.poly([(cx - 1, cy - 12), (cx + 3, cy - 3), (cx - 4, cy - 3)], f[1])
        c.poly([(cx, cy - 9), (cx + 2, cy - 3), (cx - 3, cy - 3)], f[2])
        c.poly([(cx, cy - 6), (cx + 1, cy - 3), (cx - 1, cy - 3)], f[3])
        for (x, y, k) in ((-4, -10, 0), (5, -13, 0), (2, -16, 0), (-2, -14, 1), (1, -8, 3)): c.put(cx + x, cy + y, f[k])
    elif state == 'embers':
        for (x, y) in ((0, -2), (1, -3), (-1, -2), (2, -2)): c.put(cx + x, cy + y, f[1])
        c.put(cx, cy - 3, f[2])
    for (dx, dy, rx, ry, sd) in ring[5:]: stone(dx, dy, rx, ry, sd)
    if state != 'unlit':                                    # a cooking tripod: three poles lashed at the top, a blackened pot on a chain
        mt = R('metal'); rp = R('rope')
        top = (cx, cy - 21)
        c.line(cx + 3, cy - 6, top[0], top[1], wd[1])                                    # the back pole
        c.line(cx - 12, cy + 1, top[0], top[1], wd[3]); c.line(cx + 12, cy + 1, top[0], top[1], wd[2])
        c.put(top[0], top[1] - 1, wd[3]); c.put(top[0] - 1, top[1] - 2, wd[3]); c.put(top[0] + 1, top[1] - 2, wd[2])   # pole ends past the lashing
        c.put(top[0], top[1], rp[1]); c.put(top[0], top[1] + 1, rp[0])
        for y in range(top[1] + 2, cy - 13): c.put(cx, y, mt[2] if y % 2 else mt[1])        # chain
        py = cy - 11
        c.ellipse(cx, py, 3.4, 2.4, mt[1]); c.ellipse(cx - 1, py - 0.6, 1.8, 1.2, mt[2]); c.hline(cx - 3, cx + 3, py - 2, mt[2]); c.hline(cx - 2, cx + 2, py - 2, mt[3])
        c.put(cx - 1, py - 1, mt[3]); c.hline(cx - 2, cx + 2, py + 2, mt[0]); c.put(cx + 3, py, mt[0])
        c.line(cx - 3, py - 2, cx, py - 5, mt[1]); c.line(cx + 3, py - 2, cx, py - 5, mt[1])           # bail
    name = {'burning': 'campfire', 'unlit': 'campfire_unlit', 'embers': 'campfire_embers'}[state]
    return _sprite(name, c, cx, cy + 8, shadow=None, tags=('prop', 'ysort', 'light', 'solid'), contact=(13, 2.0), ground_blend=True)


# ---------------------------------------------------------------------------------------------------------------- logs
def _log(c, x0, y0, L, r, seed, moss=True):
    """A log lying across the view, painted as a cylinder: a lit band along the top, mid tones, a dark underside;
    bark broken into irregular plates and fissures; the sawn end on the right in pale end grain with rings and a
    radial check; a rounded, shaded far end; a knot and a snapped stub; moss on the top toward the shaded end."""
    wd = R('wood'); mo = R('moss'); rng = random.Random(seed)
    for x in range(x0, x0 + L):
        for y in range(y0 - r, y0 + r + 1):
            v = (y - y0) / (r + 0.5)
            if abs(v) > 1: continue
            t = 4 if v < -0.62 else 3 if v < -0.1 else 2 if v < 0.55 else 1
            n = value_noise(x, y * 2.5, 3.0, seed)
            if n > 0.72 and -0.75 < v < 0.75: t = max(1, t - 1)                    # fissures between bark plates
            elif n < 0.12 and v < 0.2: t = min(4, t + 1)                           # a lifted plate catching light
            c.put(x, y, wd[t])
    # rounded, shaded far end
    for y in range(y0 - r, y0 + r + 1):
        c.put(x0, y, wd[1]); c.put(x0 - 1, y, wd[1]) if abs(y - y0) < r - 1 else None
    # sawn end: pale end grain, two rings, a radial check, the heart
    ex = x0 + L
    c.ellipse(ex, y0, r * 0.55 + 0.6, r + 0.5, wd[4]); c.ellipse(ex, y0, r * 0.42, r * 0.72, wd[5]); c.ellipse(ex, y0, r * 0.2, r * 0.35, wd[4])
    c.put(int(ex), y0, wd[3]); c.line(int(ex), y0, int(ex + 1), y0 - r + 1, wd[3])
    # knot and a snapped branch stub
    kx = x0 + int(L * 0.3); c.put(kx, y0 - 1, wd[0]); c.put(kx + 1, y0 - 1, wd[1]); c.put(kx, y0 - 2, wd[4])
    sx = x0 + int(L * 0.64); c.vline(sx, y0 - r - 2, y0 - r, wd[3]); c.vline(sx + 1, y0 - r - 1, y0 - r, wd[2]); c.put(sx, y0 - r - 3, wd[4])
    if moss:
        for x in range(x0 + 1, x0 + int(L * 0.45)):
            h = 1 + (value_noise(x, 0, 3.0, seed) > 0.5) + (value_noise(x, 1, 2.0, seed) > 0.75)
            for k in range(h): c.put(x, y0 - r + k, mo[2] if k == 0 else mo[1])
    m = c.a != 0
    p = np.pad(m, 1); edge = m & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
    c.a[edge] = wd[0]
    top = m & ~p[:-2, 1:-1]; c.a[top & ~np.pad(m, 1)[1:-1, :-2]] = wd[0]


def log_seat(v=0):
    """A seat log by the fire: long enough for two, worn smooth on top where people sit."""
    W, H = 40 if v == 0 else 33, 18
    c = Canvas(W, H)
    _log(c, 2, 10, W - 8, 5, seed=3 + v, moss=v == 0)
    for x in range(9, W - 12): c.put(x, 5, R('wood')[5] if x % 3 else R('wood')[4])          # polished by sitting
    return _sprite('log_seat' if v == 0 else 'log_seat_b', c, W // 2, 16, shadow=(18 if v == 0 else 15, 3, 1, 0), soft_shadow=True,
                   tags=('prop', 'ysort', 'solid'), contact=(16 if v == 0 else 13, 1.6), ground_blend=True)


def chop_block():
    """A stump kept as a chopping block, the axe left bitten into it, chips scattered at its foot."""
    W, H = 26, 24
    c = Canvas(W, H); wd = R('wood'); mt = R('metal')
    cx, top, base = 11, 9, 19
    # trunk sides with bark ridges, roots flaring at the base
    for y in range(top, base + 1):
        half = 6 + (1 if y > base - 3 else 0) + (1 if y == base else 0)
        for x in range(cx - half, cx + half + 1):
            u = (x - cx) / half
            t = 3 if u < -0.35 else 2 if u < 0.4 else 1
            if (x * 3 + y // 2) % 4 == 0: t = max(1, t - 1)
            c.put(x, y, wd[t])
    for (x, d) in ((cx - 8, -1), (cx + 8, 1)): c.put(x, base, wd[2]); c.put(x + d, base, wd[1])
    # the cut top: pale end grain with rings and a split
    c.ellipse(cx, top, 6.6, 2.8, wd[5]); c.ellipse(cx, top, 4.4, 1.8, wd[4]); c.ellipse(cx, top, 2.0, 0.9, wd[5]); c.put(cx, top, wd[3])
    c.line(cx - 4, top + 1, cx + 1, top - 1, wd[3])
    # the axe: blade bitten into the top, handle rising to the right
    c.line(cx + 1, top - 1, cx + 9, top - 9, wd[4]); c.line(cx + 2, top - 1, cx + 10, top - 9, wd[3]); c.put(cx + 10, top - 10, wd[2])
    c.rect(cx - 2, top - 3, 4, 3, mt[2]); c.hline(cx - 2, cx + 1, top - 3, mt[3]); c.put(cx - 2, top - 1, mt[1]); c.put(cx + 1, top - 1, mt[1])
    c.put(cx - 1, top - 4, mt[1]); c.put(cx, top - 4, mt[2])
    m = c.a != 0
    p = np.pad(m, 1); edge = m & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
    c.a[edge & np.isin(c.a, wd[1:])] = wd[0]; c.a[edge & np.isin(c.a, mt[1:])] = mt[0]
    # chips at its foot
    for (x, y, k) in ((cx - 9, base + 2, 5), (cx - 6, base + 3, 4), (cx + 7, base + 2, 5), (cx + 10, base + 3, 4), (cx + 4, base + 3, 5), (cx - 3, base + 4, 4), (cx + 12, base + 1, 5)):
        c.put(x, y, wd[k]); c.put(x + 1, y, wd[k - 1])
    return _sprite('chop_block', c, cx, base + 1, shadow=(9, 2.5, 2, 0), soft_shadow=True, tags=('prop', 'ysort', 'solid'), contact=(8, 1.4), ground_blend=True)


ROUND = [  # a firewood round seen end-on: bark ring (B, b underneath), pale end grain (L), growth ring (l), heart (h)
    [".BBBB.", "BLLLlB", "BLlhlB", "BLLllB", ".BbbB."],
    [".BBBB.", "BLLLLB", "BLLhlB", "BlLllB", ".bbbb."],
    [".BBB..", "BLLLB.", "BLhlB.", "BLllB.", ".bbb.."]]


def woodpile():
    """Firewood rounds stacked end-on between two stakes, kept dry under the oak: each round a ring of dark bark
    around pale end grain, the heart a darker dot; the stack settles into a gentle pyramid, a split log on top."""
    W, H = 32, 22
    c = Canvas(W, H); wd = R('wood')
    for x in (2, 28): c.vline(x, 5, 21, wd[2]); c.vline(x + 1, 4, 22, wd[1]); c.put(x, 3, wd[4]); c.put(x + 1, 3, wd[3])
    rng = random.Random(4)
    rows = [(18, [6, 11, 16, 21, 26]), (14, [8, 13, 18, 23]), (10, [11, 16, 21])]
    for (y, xs) in rows:
        for x in xs:
            px0 = x + rng.choice((0, 0, 1)) - 3; py0 = y - 2
            pat = ROUND[rng.randrange(len(ROUND))]
            for yy, row in enumerate(pat):
                for xx, ch in enumerate(row):
                    if ch != '.': c.put(px0 + xx, py0 + yy, {'B': wd[1], 'b': wd[0], 'L': wd[5], 'l': wd[4], 'h': wd[3]}[ch])
    m = c.a != 0
    p = np.pad(m, 1); edge = m & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
    c.a[edge] = wd[0]
    return _sprite('woodpile', c, 16, 21, shadow=(15, 3, 2, 0), soft_shadow=True, tags=('prop', 'ysort', 'solid'), contact=(13, 1.5), ground_blend=True)


def supply_crate():
    """A plank crate used as a table: a dented kettle and a tin mug on it, a coil of rope hanging on the side."""
    W, H = 22, 22
    c = Canvas(W, H); wd = R('wood'); mt = R('metal'); rp = R('rope'); wg = R('wood_grey')
    x0, y0, w, h = 3, 9, 15, 11
    c.rect(x0, y0, w, 3, wd[4]); c.hline(x0, x0 + w - 1, y0, wd[5])                    # lid (lit)
    c.rect(x0, y0 + 3, w, h - 3, wd[3])
    for y in (y0 + 6, y0 + 9): c.hline(x0, x0 + w - 1, y, wd[2])                       # plank joints
    c.vline(x0 + w, y0 + 1, y0 + h - 1, wd[1]); c.vline(x0 + w + 1, y0 + 2, y0 + h - 1, wd[1])   # side in shade
    for (x, y) in ((x0 + 1, y0 + 4), (x0 + w - 2, y0 + 4), (x0 + 1, y0 + 8), (x0 + w - 2, y0 + 8)): c.put(x, y, mt[3])
    # rope coil on the side
    c.ellipse(x0 + w + 1, y0 + 6, 1.6, 2.2, rp[1]); c.put(x0 + w + 1, y0 + 6, wd[1])
    # kettle
    kx, ky = x0 + 5, y0 - 1
    c.ellipse(kx, ky - 2, 3.4, 2.6, mt[2]); c.ellipse(kx - 1, ky - 3, 1.6, 1.2, mt[3])
    c.hline(kx - 1, kx + 1, ky - 5, mt[1]); c.put(kx, ky - 6, mt[1]); c.line(kx + 3, ky - 3, kx + 5, ky - 5, mt[2])
    c.line(kx - 2, ky - 5, kx - 1, ky - 6, mt[1]); c.line(kx + 2, ky - 5, kx + 1, ky - 6, mt[1])
    # tin mug
    c.rect(x0 + 10, y0 - 3, 3, 3, mt[3]); c.put(x0 + 10, y0 - 3, wg[4]); c.put(x0 + 13, y0 - 2, mt[2])
    m = c.a != 0
    p = np.pad(m, 1); edge = m & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
    c.a[edge & np.isin(c.a, wd[1:] + rp)] = wd[0]; c.a[edge & np.isin(c.a, mt[1:] + wg)] = mt[0]
    return _sprite('supply_crate', c, 11, y0 + h, shadow=(10, 2.5, 2, 0), soft_shadow=True, tags=('prop', 'ysort', 'solid'), contact=(9, 1.4))


# ---------------------------------------------------------------------------------------------------------------- rocks
def boulder(name, rx, ry, seed, mossy=False, lean=0.0):
    """A boulder that sits in the ground: planes (lit top, front, shaded flank, dark foot), a crevice or two,
    lichen on the lit side, and (mossy) a cushion of moss on top."""
    W, H = int(rx * 2 + 6), int(ry * 2 + 6)
    c = Canvas(W, H)
    cx, cy = W / 2 + lean, H / 2
    m = faceted(c, cx, cy, rx, ry, seed=seed, mossy=mossy)
    rng = random.Random(seed + 1); ys, xs = np.nonzero(m)
    for _ in range(max(1, int(rx / 4))):
        k = rng.randrange(len(xs)); x, y = int(xs[k]), int(ys[k])
        if c.a[y, x] in (R('stone')[3], R('stone')[4]): c.put(x, y, PAL.i('reed', 3) if rng.random() < 0.6 else PAL.i('flower_y', 0))
    oy = int(max(ys)) if len(ys) else int(cy + ry * 0.6)
    return _sprite(name, c, int(cx), oy, shadow=(int(rx * 1.0), max(2, int(ry * 0.4)), 2, 0), soft_shadow=True, tags=('rock', 'ysort', 'solid'),
                   contact=(rx * 0.9, max(1.2, ry * 0.2)), ground_blend=True)


def lantern_post():
    """A split-pole lantern post wedged upright with stones: a crossarm braced against the post, an iron hook, and a
    glass lantern hanging where it lights both the tent mouth and the path to the fire."""
    W, H = 20, 42
    c = Canvas(W, H); wd = R('wood'); mt = R('metal'); lg = R('lantern_glass'); st = R('stone')
    px, base = 5, 39
    for y in range(6, base + 1):                                   # the pole: lit left face, shaded right face
        c.put(px - 1, y, wd[4]); c.put(px, y, wd[3]); c.put(px + 1, y, wd[2])
        if (y * 5) % 7 == 0: c.put(px, y, wd[2])
    c.put(px - 1, 5, wd[3]); c.put(px, 5, wd[4]); c.put(px + 1, 5, wd[3])
    c.hline(px - 1, px + 12, 8, wd[3]); c.hline(px - 1, px + 12, 9, wd[1]); c.put(px + 12, 8, wd[4])        # crossarm
    c.line(px + 1, 15, px + 6, 10, wd[2]); c.line(px + 2, 15, px + 7, 10, wd[1])                             # brace
    c.put(px + 10, 10, mt[2]); c.put(px + 10, 11, mt[1]); c.put(px + 10, 12, mt[2])                           # hook and bail
    lx, ly = px + 10, 13                                                                                      # lantern
    c.hline(lx - 2, lx + 2, ly, mt[2]); c.hline(lx - 1, lx + 1, ly - 1, mt[3])
    for y in range(ly + 1, ly + 6):
        c.put(lx - 2, y, mt[1]); c.put(lx + 2, y, mt[1])
        for x in range(lx - 1, lx + 2): c.put(x, y, lg[3] if (x == lx and ly + 2 <= y <= ly + 3) else lg[2] if x == lx - 1 else lg[1])
    c.hline(lx - 2, lx + 2, ly + 6, mt[2]); c.put(lx, ly + 7, mt[1])
    # wedge stones at the foot
    for (x, y, rx, ry, sd) in ((px - 3, base - 1, 2.4, 1.8, 3), (px + 3, base, 2.6, 1.8, 5), (px, base + 1, 2.2, 1.4, 8)):
        faceted(c, x, y, rx, ry, seed=sd, top_t=4)
    m = c.a != 0
    p = np.pad(m, 1); edge = m & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
    c.a[edge & np.isin(c.a, wd[1:])] = wd[0]
    return _sprite('lantern_post', c, px, base + 1, shadow=(5, 2, 3, 0), soft_shadow=True, tags=('structure', 'ysort', 'light', 'solid'), contact=(4, 1.2))


def add_camp_art(lib):
    for s in (tent(), lantern_post(), campfire('burning'), campfire('embers'), campfire('unlit'), log_seat(0), log_seat(1), chop_block(), woodpile(), supply_crate(),
              boulder('rock_xl', 18, 12, 41), boulder('rock_l0', 13, 9, 3), boulder('rock_l1', 11, 8, 8, mossy=True), boulder('rock_m0', 8, 6, 12), boulder('rock_m1', 7, 5.5, 15, mossy=True),
              boulder('step_stone', 7.5, 3.2, 31), boulder('rock_s0', 4.5, 3.4, 21), boulder('rock_s1', 3.6, 2.8, 24), boulder('rock_s2', 5, 3.2, 27, mossy=True)):
        lib[s.name] = s
    add_plants(lib); add_trees(lib)
    from .tree_art import add_trees as _grown; _grown(lib)
    from .world_art import add_world_art; add_world_art(lib)              # oaks, birches, willows, the dead snag: grown, with their own winter selves
    for s_ in (forage_basket(), water_bucket()): lib[s_.name] = s_
    return lib


# ---------------------------------------------------------------------------------------------------------------- plants
def _curve(c, x0, y0, ang, L, bend, col_fn, step=0.5):
    """Walk a curve from (x0, y0) at angle ang (radians, 0 = up), bending by `bend` per unit; col_fn(t, x, y)
    paints each new pixel (t = 0 at the base, 1 at the tip). Returns the pixels visited."""
    pts = []; x, y = float(x0), float(y0); a = ang; n = int(L / step)
    last = None
    for i in range(n + 1):
        t = i / max(1, n); px, py = int(round(x)), int(round(y))
        if (px, py) != last: col_fn(t, px, py); pts.append((px, py, t)); last = (px, py)
        x += math.sin(a) * step; y -= math.cos(a) * step; a += bend * step
    return pts


def fern(name, seed, size=1.0):
    """A fern: five fronds rising from one crown in a fan, each arching outward; every frond is a dark rib with
    paired leaflets that slant toward the tip and shorten along it, lit on the side facing up. The centre fronds are
    behind, the outer ones in front and lower."""
    W, H = int(26 * size), int(20 * size)
    c = Canvas(W, H); f = R('fern'); rng = random.Random(seed)
    bx, by = W // 2, H - 2
    fronds = [(0.0, 15, 0.0), (-0.32, 15, -0.03), (0.32, 15, 0.03), (-0.72, 13, -0.05), (0.72, 13, 0.05)]
    for (ang, L, bend) in fronds:
        ang += rng.uniform(-0.08, 0.08); L *= size * rng.uniform(0.9, 1.05)
        pts = _curve(c, bx + int(ang * 2), by, ang, L, bend, lambda t, x, y: None, step=0.5)
        for k, (x, y, t) in enumerate(pts):
            if k % 2 == 0 and 0.08 < t < 0.95:
                x2, y2, _ = pts[min(len(pts) - 1, k + 2)]; dx, dy = x2 - x, y2 - y
                n_ = math.hypot(dx, dy) or 1; ux, uy = dx / n_, dy / n_          # along the frond (toward the tip)
                ln = int(round((1 - t) * 2.2 * size + 0.6))
                for side in (-1, 1):
                    nx, ny = -uy * side, ux * side                               # perpendicular, slanted forward
                    up = ny < 0 or (abs(ny) < 0.2 and side == (1 if ang < 0 else -1))
                    for j in range(1, ln + 1):
                        px = int(round(x + (nx * 0.85 + ux * 0.55) * j)); py = int(round(y + (ny * 0.85 + uy * 0.55) * j))
                        if 0 <= px < W and 0 <= py < H: c.put(px, py, (f[4] if t > 0.6 else f[3]) if up else f[1])
            if 0 <= x < W and 0 <= y < H: c.put(x, y, f[1] if t < 0.7 else f[2])
    m = c.a != 0; p = np.pad(m, 1)
    c.a[m & ~p[2:, 1:-1]] = f[0]
    c.ellipse(bx, by, 2.2, 1.1, f[0])
    return _sprite(name, c, bx, by + 1, shadow=(int(7 * size), 2, 1, 0), soft_shadow=True, tags=('plant', 'ysort'), contact=(4 * size, 1.0))


def grass_clump(name, seed, size=1.0, flowers=0):
    """Tall grass: ten to fourteen blades rising from a dark root, leaning and arching, darker inside, lighter at
    the tips; flowers > 0 adds that many seed heads (oat-coloured) to the tallest blades."""
    W, H = int(18 * size), int(16 * size)
    c = Canvas(W, H); g = R('grass'); rng = random.Random(seed); rd = R('reed')
    bx, by = W // 2, H - 2
    n = int(12 * size)
    blades = sorted([(rng.uniform(-0.9, 0.9), rng.uniform(5, 12) * size, rng.uniform(-0.08, 0.08)) for _ in range(n)], key=lambda q: abs(q[0]), reverse=True)
    tips = []
    for (ang, L, bend) in blades:
        x0 = bx + int(ang * 3)
        deep = abs(ang) < 0.35
        def col(t, x, y, deep=deep):
            if 0 <= x < W and 0 <= y < H: c.put(x, y, g[2] if t < 0.25 else (g[3] if deep else g[4]) if t < 0.7 else (g[4] if deep else g[5]))
        pts = _curve(c, x0, by, ang * 0.7, L, bend + ang * 0.05, col)
        if pts: tips.append((pts[-1], L))
    for (p_, L) in sorted(tips, key=lambda q: -q[1])[:flowers]:
        x, y, _ = p_
        for (dx, dy, k) in ((0, 0, 3), (0, -1, 3), (1, 0, 2), (-1, 1, 2)): 
            if 0 <= x + dx < W and 0 <= y + dy < H: c.put(x + dx, y + dy, rd[k])
    c.hline(bx - 2, bx + 2, by, g[1]); c.hline(bx - 1, bx + 1, by + 1, g[1])
    return _sprite(name, c, bx, by + 1, shadow=(int(5 * size), 1.5, 1, 0), soft_shadow=True, tags=('plant', 'ysort', 'grass'), contact=(3, 0.8))


FLOWER = {   # petals light/mid/dark and centre
    'daisy': (('flower_w', 2), ('flower_w', 1), ('flower_w', 0), ('flower_y', 1)),
    'blue': (('flower_b', 2), ('flower_b', 1), ('flower_b', 0), ('flower_w', 2)),
    'butter': (('flower_y', 2), ('flower_y', 1), ('flower_y', 0), ('flower_y', 0)),
    'pink': (('flower_p', 2), ('flower_p', 1), ('flower_p', 0), ('flower_y', 2)),
}


def flower_patch(name, kind, seed, n=5, spread=6):
    """A small colony of one flower: several heads at different heights on thin stems, leaves at the foot. Flowers
    grow in patches, so the patch is the unit, not the single flower."""
    W, H = spread * 2 + 8, 15
    c = Canvas(W, H); g = R('grass'); rng = random.Random(seed); L_, M_, D_, C_ = [PAL.i(*q) for q in FLOWER[kind]]
    bx, by = W // 2, H - 2
    heads = []
    for k in range(n):
        x = bx + int(rng.uniform(-spread, spread)); h = rng.randint(4, 9)
        heads.append((x, by - h, h))
    heads.sort(key=lambda q: q[1])
    for (x, yh, h) in heads:                                                  # stems
        lean = rng.choice((-1, 0, 0, 1))
        for y in range(yh + 1, by + 1):
            c.put(x + (lean if y < yh + 2 else 0), y, g[3] if y < by - 1 else g[2])
    for k in range(n * 2 + 2):                                                # a low clump of leaves at the foot
        x = bx + int(rng.uniform(-spread - 1, spread + 1)); y = by - rng.randint(0, 2)
        c.put(x, y, g[4] if y < by else g[3]); c.put(x + rng.choice((-1, 1)), y - 1, g[4] if rng.random() < 0.6 else g[5]); c.put(x, by + 1, g[1])
    for (x, yh, h) in heads:                                                  # heads: back ones first
        if kind == 'daisy':
            for (dx, dy, col) in ((0, -1, L_), (-1, 0, L_), (1, 0, M_), (0, 1, M_), (0, 0, C_)): c.put(x + dx, yh + dy, col)
        elif kind == 'blue':                                                   # bells hang
            for (dx, dy, col) in ((0, 0, M_), (1, 0, D_), (0, 1, L_), (1, 1, M_)): c.put(x + dx, yh + dy, col)
        else:
            for (dx, dy, col) in ((0, 0, L_), (1, 0, M_), (0, 1, M_), (1, 1, D_)): c.put(x + dx, yh + dy, col)
            c.put(x, yh, C_) if kind == 'butter' and rng.random() < 0.5 else None
    return _sprite(name, c, bx, by + 1, shadow=None, tags=('plant', 'ysort', 'flower'))


def mushroom_cluster(name, seed, red=False):
    """Three mushrooms of different ages growing together from damp ground: caps lit on top with a darker rim,
    pale stems with a shadow under the cap, (red) white spots; moss at their feet."""
    W, H = 16, 12
    c = Canvas(W, H); sh = R('shroom'); ss = R('shroom_stem'); mo = R('moss'); rng = random.Random(seed)
    cap = (sh if red else R('wood'))
    for (x, base, cw, ch, st_h) in ((5, 10, 3.2, 2.0, 3), (10, 10, 2.4, 1.6, 2), (12, 11, 1.6, 1.0, 1)):
        for y in range(base - st_h, base + 1): c.put(x, y, ss[1]); c.put(x + 1, y, ss[0]) if cw > 2 else None
        cy = base - st_h - 1
        c.ellipse(x + 0.5, cy, cw, ch, cap[2] if red else cap[3])
        c.ellipse(x - 0.3, cy - 0.6, cw * 0.6, ch * 0.55, cap[3] if red else cap[4])
        c.hline(int(x + 0.5 - cw + 1), int(x + 0.5 + cw - 1), int(cy + ch - 0.5), cap[1] if red else cap[1])
        if red:
            for (dx, dy) in ((-1, -1), (1, 0), (0, -2)): c.put(int(x + dx), int(cy + dy), ss[2])
    for x in range(2, 14): c.put(x, 11, mo[1] if x % 3 else mo[2])
    m = c.a != 0; p = np.pad(m, 1); edge = m & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
    c.a[edge & np.isin(c.a, cap[1:] if not red else sh[1:])] = cap[0]
    return _sprite(name, c, 8, 12, shadow=None, tags=('plant', 'ysort', 'mushroom'))


def bush(name, seed, w=24, h=18, berries=False):
    """A rounded shrub built from overlapping leaf clumps: dark core, mid clumps, lit clumps on the upper left, a few
    single leaves breaking the silhouette, (berries) red fruit tucked in the shade side."""
    c = Canvas(w + 4, h + 4); s_ = R('shrub'); rng = random.Random(seed)
    cx, by = (w + 4) / 2, h + 1
    clumps = []
    for k in range(9):
        a = rng.uniform(math.pi * 0.95, math.pi * 2.05); rr = rng.uniform(0.2, 0.7)
        x = cx + math.cos(a) * w * 0.34 * rr * 1.6; y = by - h * 0.45 + math.sin(a) * h * 0.38 * rr * 1.4
        clumps.append((x, y, rng.uniform(4.0, 6.0) * w / 24, rng.uniform(3.4, 4.6) * h / 18))
    c.ellipse(cx, by - h * 0.42, w * 0.47, h * 0.45, s_[1])
    for (x, y, rx, ry) in sorted(clumps, key=lambda q: q[1]):
        lit_blob(c, x, y, rx, ry, s_, seed=int(x * 7 + y), rough=0.3, lo=1, hi=4, outline=False)
    m = c.a != 0
    for k in range(6):                                                         # stray leaves on the rim
        ys, xs = np.nonzero(m); i = rng.randrange(len(xs)); x, y = int(xs[i]), int(ys[i])
        for (dx, dy) in ((0, -1), (-1, 0), (1, 0)):
            if 0 <= x + dx < c.w and 0 <= y + dy < c.h and not m[y + dy, x + dx]: c.put(x + dx, y + dy, s_[3] if dy < 0 else s_[2]); break
    if berries:
        for k in range(7):
            ys, xs = np.nonzero(c.a == s_[2]); i = rng.randrange(len(xs)); c.put(int(xs[i]), int(ys[i]), PAL.i('berry', 1)); c.put(int(xs[i]) + 1, int(ys[i]), PAL.i('berry', 0)) if rng.random() < 0.5 else None
    m = c.a != 0
    sel_outline(c, m, s_)
    return _sprite(name, c, int(cx), by + 1, shadow=(int(w * 0.45), 3, 2, 0), soft_shadow=True, tags=('plant', 'ysort', 'shrub', 'solid'), contact=(w * 0.38, 1.4))


def add_plants(lib):
    for s in (fern('fern_a', 1), fern('fern_b', 2, 0.85), fern('fern_c', 3, 1.15), grass_clump('tall_a', 1), grass_clump('tall_b', 2, 0.85), grass_clump('tall_c', 3, 1.1, flowers=3),
              flower_patch('patch_daisy', 'daisy', 1, 9, 7), flower_patch('patch_daisy_s', 'daisy', 4, 5, 4), flower_patch('patch_blue', 'blue', 2, 8, 6),
              flower_patch('patch_butter', 'butter', 3, 8, 6), flower_patch('patch_pink', 'pink', 5, 7, 5),
              mushroom_cluster('shrooms_brown', 1), mushroom_cluster('shrooms_red', 2, red=True),
              bush('bush_a', 1), bush('bush_b', 2, 20, 15), bush('bush_berry', 3, 22, 17, berries=True)):
        lib[s.name] = s
    return lib


# the composition rules and the rest of the map ask for plants and stones by their older names; they now get these
ALIASES = {'rowan_0': 'rowan_new0', 'rowan_1': 'rowan_new1', 'pine_0': 'pine_new0', 'pine_1': 'pine_new1', 'fern_0': 'fern_a', 'fern_1': 'fern_b', 'fern_2': 'fern_c', 'tallgrass_0': 'tall_a', 'tallgrass_1': 'tall_b', 'tallgrass_2': 'tall_c',
           'flowers_w0': 'patch_daisy', 'flowers_w1': 'patch_daisy_s', 'flowers_b0': 'patch_blue', 'flowers_b1': 'patch_blue',
           'flowers_y0': 'patch_butter', 'flowers_y1': 'patch_butter', 'flowers_p0': 'patch_pink', 'flowers_p1': 'patch_pink',
           'shroom_0': 'shrooms_brown', 'shroom_1': 'shrooms_red', 'shrub_0': 'bush_a', 'shrub_1': 'bush_b', 'shrub_2': 'bush_berry',
           'boulder_l0': 'rock_l0', 'boulder_l1': 'rock_l1', 'boulder_m0': 'rock_m0', 'boulder_m1': 'rock_m1', 'boulder_s0': 'rock_s0', 'boulder_s1': 'rock_s1',
           'boulder_mossy_l0': 'rock_l1', 'boulder_mossy_l1': 'rock_l1', 'boulder_mossy_m0': 'rock_m1', 'boulder_mossy_m1': 'rock_m1', 'stone_0': 'rock_s1', 'stone_1': 'rock_s2'}


# ---------------------------------------------------------------------------------------------------------------- trees
def _trunk(c, cx, top, base, half, wd=None):
    """A trunk that flares into roots: lit left edge, shaded right, bark streaks, two roots gripping the ground."""
    wd = wd or R('wood')
    for y in range(top, base + 1):
        flare = max(0, (y - (base - 4))) * 0.7
        hw = half + flare
        for x in range(int(cx - hw), int(cx + hw) + 1):
            u = (x - cx) / max(1, hw)
            t = 3 if u < -0.4 else 2 if u < 0.35 else 1
            if (x * 5 + y * 3) % 7 == 0: t = max(1, t - 1)
            c.put(x, y, wd[t])
    for (dx, k) in ((-half - 3, 2), (half + 3, 1)):
        c.put(int(cx + dx), base, wd[k]); c.put(int(cx + dx * 0.8), base - 1, wd[k])


def small_tree(name, fam, seed, w=30, h=40, berries=False):
    """A young broadleaf (rowan in the meadow): a trunk with a fork, a crown of overlapping leaf clumps lit from the
    upper left with a dark underside, gaps where branches show, and (berries) bunches of red fruit at the rim."""
    W, H = w + 6, h + 4
    c = Canvas(W, H); lv = R(fam); rng = random.Random(seed); wd = R('wood')
    cx, base = W // 2, H - 2
    ctop, cbot = 2, int(H * 0.70)
    _trunk(c, cx, cbot - 6, base, 2.0)
    c.line(cx, cbot - 2, cx - 5, cbot - 9, wd[2]); c.line(cx + 1, cbot - 2, cx + 6, cbot - 10, wd[1])       # the fork
    ccx, ccy, crx, cry = cx, (ctop + cbot) / 2, w * 0.46, (cbot - ctop) / 2
    c2 = Canvas(W, H)
    lit_blob(c2, ccx, ccy + 1, crx, cry * 0.92, lv, seed=seed, rough=0.5, lo=1, hi=2, outline=False)     # the shaded mass
    clumps = []
    for k in range(15):
        a = rng.uniform(math.pi * 0.9, math.pi * 2.1) if k < 9 else rng.uniform(0, 2 * math.pi); rr = rng.uniform(0.45, 0.92) if k < 9 else rng.uniform(0.0, 0.5)
        clumps.append((ccx + math.cos(a) * crx * rr, ccy + math.sin(a) * cry * rr - 1, rng.uniform(3.6, 5.2) * w / 30, rng.uniform(3.0, 4.2) * h / 40))
    for (x, y, rx, ry) in sorted(clumps, key=lambda q: q[1] + q[0] * 0.2):
        cm = lit_blob(c2, x, y, rx, ry, lv, seed=int(x * 13 + y * 7), rough=0.4, lo=2, hi=4 if y < ccy + 2 else 3, outline=False)
        p_ = np.pad(cm, 1); rim = cm & (~p_[2:, 1:-1] | ~p_[1:-1, 2:])
        c2.a[rim] = lv[1]                                                   # each clump's own shaded lower rim: layered foliage
    m = c2.a != 0
    sel_outline(c2, m, lv)
    ys, xs = np.nonzero(m)
    under = m & (np.arange(H)[:, None] > ccy + cry * 0.5)
    c2.a[under & (c2.a != lv[0])] = lv[1]                                                              # the dark underside
    if berries:
        for k in range(8):
            i = rng.randrange(len(xs)); x, y = int(xs[i]), int(ys[i])
            if c2.a[y, x] in (lv[2], lv[3]) and y > ccy - cry * 0.3:
                for (dx, dy) in ((0, 0), (1, 0), (0, 1), (1, 1)): c2.put(x + dx, y + dy, PAL.i('berry', 1))
    c.a[m] = c2.a[m]
    tm = np.isin(c.a, wd); p = np.pad(c.a != 0, 1)
    edge = (c.a != 0) & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
    c.a[edge & tm] = wd[0]
    return _sprite(name, c, cx, base + 1, shadow=(int(w * 0.42), 4, 5, -1), soft_shadow=True, tags=('tree', 'ysort'), contact=(4, 1.5))


def pine(name, seed, w=30, h=52):
    """A fir: five tiers of drooping boughs, each a fan with a jagged hem, lit on the left, dark in the core and at the
    hem where the tier above shades it; a straight trunk at the foot."""
    W, H = w + 4, h + 4
    c = Canvas(W, H); pn = R('pine'); rng = random.Random(seed)
    cx, base = W // 2, H - 2
    _trunk(c, cx, base - 7, base, 1.4)
    tiers = 5; top = 2; bot = base - 6
    for k in range(tiers):
        t0 = top + (bot - top) * k / tiers * 0.92; t1 = top + (bot - top) * (k + 1) / tiers + 3
        hw = (w / 2) * (0.38 + 0.62 * (k + 1) / tiers)
        for y in range(int(t0), int(t1) + 1):
            v = (y - t0) / max(1, t1 - t0)
            half = hw * (0.25 + 0.75 * v)
            for x in range(int(cx - half), int(cx + half) + 1):
                u = (x - cx) / max(1, half)
                jag = (value_noise(x, k, 1.6, seed) - 0.5) * 3
                if v > 0.82 and (y - t1 + 2) > jag: continue                  # the jagged hem
                tone = 4 if u < -0.45 else 3 if u < 0.05 else 2 if u < 0.55 else 1
                if v > 0.7: tone = max(1, tone - 1)
                if abs(u) < 0.12 and v < 0.5: tone = max(1, tone - 1)
                c.put(x, y, pn[tone])
    c.vline(cx, 0, 2, pn[3]); c.put(cx, 0, pn[4])
    m = c.a != 0; m &= np.isin(c.a, pn)
    sel_outline(c, m, pn)
    return _sprite(name, c, cx, base + 1, shadow=(int(w * 0.4), 4, 5, -1), soft_shadow=True, tags=('tree', 'ysort'), contact=(3, 1.2))


def add_trees(lib):
    for s in (small_tree('rowan_new0', 'rowan', 5, berries=True), small_tree('rowan_new1', 'rowan', 9, 26, 36, berries=True),
              pine('pine_new0', 3), pine('pine_new1', 7, 26, 46)):
        lib[s.name] = s
    return lib


def forage_basket():
    """A woven basket set down by the crate: wicker in two tones with a lit rim, filled with the day's finds
    (brown mushrooms, blackberries, a fern frond sticking out)."""
    W, H = 14, 12
    c = Canvas(W, H); rp = R('rope'); wd = R('wood'); sh = R('wood'); f = R('fern')
    cx, by = 7, 10
    for y in range(4, by + 1):                                   # the weave
        hw = 5 - (1 if y > by - 2 else 0)
        for x in range(cx - hw, cx + hw + 1):
            c.put(x, y, rp[2] if (x + y) % 2 == 0 and y < by - 1 else rp[1])
    c.hline(cx - 5, cx + 5, 4, rp[2]); c.hline(cx - 5, cx + 5, 5, rp[0])
    c.line(cx - 5, 4, cx - 3, 0, rp[1]); c.line(cx + 5, 4, cx + 3, 0, rp[1]); c.hline(cx - 3, cx + 3, 0, rp[1])   # handle
    for (x, y, col) in ((cx - 3, 3, sh[3]), (cx - 2, 3, sh[4]), (cx - 3, 2, sh[4]), (cx + 1, 3, PAL.i('berry', 0)), (cx + 2, 3, PAL.i('flower_p', 0)), (cx + 2, 2, PAL.i('berry', 0)),
                        (cx + 3, 3, PAL.i('berry', 1)), (cx, 3, sh[3])):
        c.put(x, y, col)
    c.line(cx + 4, 3, cx + 6, 0, f[3]); c.put(cx + 5, 1, f[2])
    m = c.a != 0; p = np.pad(m, 1); edge = m & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
    c.a[edge & np.isin(c.a, rp)] = wd[1]
    return _sprite('forage_basket', c, cx, by + 1, shadow=(5, 1.5, 1, 0), soft_shadow=True, tags=('prop', 'ysort'), contact=(4, 1.0))


def water_bucket():
    """A wooden bucket with iron hoops, water catching the sky, a dipper hanging on the rim."""
    W, H = 11, 12
    c = Canvas(W, H); wd = R('wood'); mt = R('metal'); wa = R('water')
    for y in range(3, 11):
        hw = 3 + (1 if y < 6 else 0)
        for x in range(5 - hw, 5 + hw + 1):
            u = (x - 5) / max(1, hw); c.put(x, y, wd[4] if u < -0.4 else wd[3] if u < 0.4 else wd[2])
    for y in (4, 9): c.hline(1, 9, y, mt[2])
    c.ellipse(5, 3, 4, 1.4, wa[3]); c.hline(3, 6, 3, wa[4])
    c.line(8, 2, 10, 0, wd[2])
    m = c.a != 0; p = np.pad(m, 1); edge = m & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
    c.a[edge & np.isin(c.a, wd[1:] + mt[1:])] = wd[0]
    return _sprite('water_bucket', c, 5, 11, shadow=(4, 1.5, 1, 0), soft_shadow=True, tags=('prop', 'ysort'), contact=(3, 1.0))



def winter_dry(sprite):
    """Winter keeps a plant's shape but takes its green: blades go to straw and dry brown, tips to pale stalk."""
    import dataclasses
    c = sprite.c.copy(); a = c.a
    straw = R('rope'); dry = R('wood')
    for fam in ('grass', 'reed', 'shrub', 'fern', 'lily'):
        ramp = R(fam)
        for k, idx in enumerate(ramp):
            t = k / max(1, len(ramp) - 1)
            a[a == idx] = dry[1] if t < 0.25 else straw[0] if t < 0.5 else straw[1] if t < 0.8 else straw[2]
    return dataclasses.replace(sprite, c=c, name=sprite.name + '_winter', tags=tuple(sprite.tags) + ('winter',))
