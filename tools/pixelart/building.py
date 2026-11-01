"""Construction art: connecting walls, foundations, floors, roofs, fences, furniture, stations.
Tile pieces are authored as periodic 16 px patterns so connected runs have no seams.
Geometry (3/4 view): a wall cell's ground centre is sprite row 35, its cap is 24 px up at row 11,
its visible face ends at row 38. Mask bits: N=1 E=2 S=4 W=8."""
from __future__ import annotations
import random
import numpy as np
from .canvas import Canvas, refine
from .palette import PAL
R = PAL.ramp
N, E, S, W_ = 1, 2, 4, 8
WALLS = ['wood', 'reinforced', 'stone', 'metal', 'cottage']

def face_px(mat, x, y):
    """Wall face pattern, periodic in x (16) so runs are seamless. y is rows below the cap."""
    w, st, mt, mr, wg, cv = R('wood'), R('stone'), R('metal'), R('metal_rust'), R('wood_grey'), R('canvas')
    if mat in ('wood', 'reinforced'):
        row = y // 5; k = y % 5; off = (row * 7) % 16
        seam = (x + off) % 16 in (0,)
        v = w[1] if k == 4 or seam else (w[4] if k == 0 else (w[3] if (x * 3 + row * 5) % 11 else w[2]))
        if mat == 'reinforced' and y in (6, 7, 17, 18):
            v = mt[2] if y in (6, 17) else mt[1]
            if x % 8 == 3 and y in (6, 17): v = mt[3]
        return v
    if mat == 'stone':
        row = y // 5; k = y % 5; off = 0 if row % 2 else 4; b = (x + off) % 8
        if k == 4 or b == 7: return st[1]
        tone = 3 if ((x + off) // 8 + row) % 3 else 2
        return st[tone + 1] if k == 0 else st[tone]
    if mat == 'metal':
        px = x % 8; row = y // 8; k = y % 8
        if k == 7 or px == 7: return mt[0]
        if k == 0: return wg[3]
        if px == 1 and k == 1: return mt[3]
        if (x * 5 + y * 3) % 23 == 0: return mr[1]
        return wg[2] if (x // 8 + row) % 2 else wg[1]
    # cottage: pale plaster in a dark timber frame
    if y % 12 in (0, 1) or x % 16 in (0, 1): return w[1] if (y % 12 == 1 or x % 16 == 1) else w[2]
    if (x - 2 - (y % 12)) % 12 in (0, 1) and (x % 16) < 13: return w[2]
    return cv[5] if y % 12 == 2 else (cv[4] if (x * 7 + y * 11) % 19 else cv[3])

def cap_ramp(mat):
    return {'wood': R('wood'), 'reinforced': R('wood'), 'stone': R('stone'), 'metal': R('wood_grey'), 'cottage': R('wood')}[mat]

def wall(mat, mask, kind='wall'):
    c = Canvas(16, 44); r = cap_ramp(mat)
    x0 = 0 if mask & W_ else 4; x1 = 15 if mask & E else 11
    # front face first
    for x in range(x0, x1 + 1):
        if mask & S and 4 <= x <= 11: continue
        for y in range(14, 39): c.put(x, y, face_px(mat, x, y - 14))
    # shaded top of the face under the cap, lit left end, dark right end
    for x in range(x0, x1 + 1):
        if not (mask & S and 4 <= x <= 11): c.put(x, 14, PAL.shade[c.get(x, 14)]); c.put(x, 15, PAL.shade[c.get(x, 15)])
    # cap
    capm = Canvas(16, 44)
    capm.rect(x0, 8, x1 - x0 + 1, 6, 1)
    if mask & N: capm.rect(4, 0, 8, 8, 1)
    if mask & S: capm.rect(4, 14, 8, 10, 1)
    for y in range(44):
        for x in range(16):
            if capm.a[y, x]:
                c.put(x, y, r[3] if (x + y * 3) % 13 else r[2])
    # cap light: lit along north edges, dark along south edges
    H, W = capm.a.shape
    for y in range(H):
        for x in range(W):
            if not capm.a[y, x]: continue
            up = y > 0 and capm.a[y - 1, x] or y == 0; dn = y < H - 1 and capm.a[y + 1, x]
            lf = x > 0 and capm.a[y, x - 1] or x == 0; rt = x < W - 1 and capm.a[y, x + 1] or x == W - 1
            if not up: c.put(x, y, r[4])
            elif not lf: c.put(x, y, r[4])
            if not dn or not rt: c.put(x, y, r[1])
    # end posts for free ends
    for x, cond in ((x0, not (mask & W_)), (x1, not (mask & E))):
        if cond:
            for y in range(14, 39):
                if c.get(x, y): c.put(x, y, r[1] if x == x1 else r[3])
    if kind == 'window':
        fr = R('wood'); ti = R('tent_interior'); ic = R('ice')
        c.rect(3, 18, 10, 12, fr[2]); c.hline(3, 12, 18, fr[4]); c.vline(3, 18, 29, fr[3]); c.vline(12, 18, 29, fr[1]); c.hline(2, 13, 30, fr[3]); c.hline(2, 13, 31, fr[1])   # frame + sill
        c.rect(4, 19, 8, 10, ti[1]); c.rect(4, 19, 8, 2, ti[0])
        c.vline(7, 19, 28, fr[2]); c.vline(8, 19, 28, fr[1]); c.hline(4, 11, 23, fr[2])    # muntins
        c.put(5, 20, ic[3]); c.put(5, 21, ic[4]); c.put(6, 20, ic[3]); c.put(10, 25, ic[2])  # glint on the glass
    if kind in ('door_closed', 'door_open'):
        fr = R('wood'); mt = R('metal')
        strong = mat in ('reinforced', 'metal', 'stone')
        c.rect(3, 16, 10, 23, 0)
        c.rect(2, 15, 12, 2, fr[3]); c.hline(2, 13, 15, fr[4]); c.rect(2, 17, 2, 22, fr[2]); c.vline(2, 17, 38, fr[3]); c.rect(12, 17, 2, 22, fr[1])   # lintel + jambs
        if kind == 'door_closed':
            for x in range(4, 12):
                for y in range(17, 39):
                    c.put(x, y, fr[1] if x in (6, 9) else (fr[3] if x in (4, 7, 10) else fr[2]))
            for y in (21, 33):
                c.hline(4, 11, y, mt[2] if strong else fr[1]); c.put(5, y, mt[3])
            c.put(10, 28, R('lantern_glass')[1]); c.put(10, 29, mt[1])                     # latch
        else:
            for y in range(17, 39): c.put(4, y, fr[3]); c.put(5, y, fr[1])                 # leaf swung inward
    return c

def fence(mask, kind='fence'):
    c = Canvas(16, 24); w = R('wood'); mt = R('metal')
    if kind in ('gate_closed', 'rgate_closed', 'gate_open', 'rgate_open'):
        strong = kind.startswith('r')
        for x in (0, 13): c.rect(x, 4, 3, 16, w[2]); c.vline(x, 4, 19, w[3]); c.vline(x + 2, 4, 19, w[1]); c.hline(x, x + 2, 3, w[4])
        if kind.endswith('closed'):
            for x in range(3, 13, 2):
                c.rect(x, 7, 1, 12, w[3]); c.put(x, 6, w[4])
                c.rect(x + 1, 7, 1, 12, w[2])
            for y in (9, 15): c.hline(3, 12, y, mt[2] if strong else w[1]); c.hline(3, 12, y + 1, mt[1] if strong else w[1])
            if strong: c.put(5, 9, mt[3]); c.put(10, 15, mt[3])
        return c
    if mask & E: c.rect(8, 9, 8, 2, w[3]); c.hline(8, 15, 10, w[1]); c.rect(8, 14, 8, 2, w[3]); c.hline(8, 15, 15, w[1])
    if mask & W_: c.rect(0, 9, 8, 2, w[3]); c.hline(0, 7, 10, w[1]); c.rect(0, 14, 8, 2, w[3]); c.hline(0, 7, 15, w[1])
    if mask & N: c.rect(7, 0, 2, 9, w[3]); c.vline(8, 0, 8, w[1])
    if mask & S: c.rect(7, 12, 2, 12, w[3]); c.vline(8, 12, 23, w[1])
    c.rect(6, 5, 4, 15, w[2]); c.vline(6, 5, 19, w[3]); c.vline(9, 5, 19, w[1]); c.hline(6, 9, 4, w[4]); c.hline(7, 8, 3, w[3]); c.hline(6, 9, 19, w[0])
    return c

def foundation(mat, mask):
    """Top surface + a visible south lip that meets the soil. mask uses E,S,W only."""
    c = Canvas(16, 20); w, st, mt, dr = R('wood'), R('stone'), R('metal'), R('dirt')
    for y in range(16):
        for x in range(16):
            if mat == 'stone':
                b = (x + (0 if (y // 8) % 2 else 8)) % 16
                c.put(x, y, st[1] if (y % 8 == 7 or b % 16 == 15) else (st[3] if y % 8 == 0 else st[2]))
            else:
                c.put(x, y, w[1] if y % 8 == 7 else (w[3] if y % 8 == 0 else w[2]))
    if not mask & S:
        for x in range(16):
            for y, v in ((16, st[3] if mat == 'stone' else w[2]), (17, st[2] if mat == 'stone' else w[1]), (18, st[1] if mat == 'stone' else w[0]), (19, dr[1])):
                if mat == 'stone' and x % 8 == 7 and y < 19: v = st[0]
                if mat == 'reinforced' and y == 17 and x % 8 == 2: v = mt[3]
                c.put(x, y, v)
        c.hline(0, 15, 15, st[4] if mat == 'stone' else w[4])
    for y in range(20 if not mask & S else 16):
        if not mask & W_: c.put(0, y, st[3] if mat == 'stone' else w[3])
        if not mask & E: c.put(15, y, st[1] if mat == 'stone' else w[0])
    return c

def floor(kind):
    c = Canvas(16, 16); w, st, cv = R('wood'), R('stone'), R('canvas')
    for y in range(16):
        for x in range(16):
            if kind == 'plank':
                row = y // 4; v = w[2] if y % 4 == 3 or (x + row * 5) % 16 == 0 else (w[4] if (x * 3 + row * 7) % 17 == 0 else w[3])
            elif kind == 'flag':
                b = (x + (y // 8) * 4) % 8
                v = st[1] if y % 8 == 7 or b == 7 else (st[4] if y % 8 == 0 else st[3])
            else:  # cottage: warm checker tile
                v = cv[1] if x % 8 == 7 or y % 8 == 7 else (cv[3] if (x // 8 + y // 8) % 2 else cv[4])
            c.put(x, y, v)
    return c

ROOF_PARTS = ['north', 'ridge', 'south', 'eave']
def roof(mat, part, left, right):
    """20 x 22, cell at cols 2..17; overhangs 2 px at free ends and 4 px at the south eave."""
    c = Canvas(20, 22)
    fam = {'thatch': R('reed'), 'shingle': R('leaf_litter'), 'slate': R('stone')}[mat]
    base = len(fam) // 2; sh = fam[max(0, base - 1)]; dk = fam[0]; mid = fam[base]; hi = fam[min(len(fam) - 1, base + 1)]
    x0 = 0 if left else 2; x1 = 19 if right else 17
    y1 = 19 if part == 'eave' else 15
    for y in range(0, y1 + 1):
        for x in range(x0, x1 + 1):
            cx = x - 2
            row = y // 4; k = y % 4; st = (cx + (row % 2) * 3) % 6
            if mat == 'thatch':
                # bundled straw courses: a soft shaded line under each course, broken strands, no per-pixel noise
                v = sh if k == 3 and st != 2 else (hi if k == 0 and st in (1, 2, 4) else mid)
                if k == 3 and st == 0: v = dk
            else:
                v = dk if k == 3 or st == 5 else (hi if k == 0 else mid)
            if part == 'north' and v != dk: v = hi if v == mid else v           # north slope catches the sky: lighter
            c.put(x, y, v)
    if part == 'north':
        for y in range(0, 5):
            if left:
                for x in range(0, 5 - y): c.put(x, y, 0)
            if right:
                for x in range(15 + y, 20): c.put(x, y, 0)
    if part == 'ridge':
        c.rect(x0, 5, x1 - x0 + 1, 5, fam[min(len(fam) - 1, base + 1)]); c.hline(x0, x1, 5, fam[-1]); c.hline(x0, x1, 9, dk); c.hline(x0, x1, 10, dk)
    if part == 'eave':
        wd = R('wood')
        c.hline(x0, x1, 18, wd[2]); c.hline(x0, x1, 19, wd[1]); c.hline(x0, x1, 20, wd[0])     # fascia board
        for x in range(x0, x1 + 1, 4): c.put(x, 21, wd[0])                                       # rafter tails
    ys0 = 5 if part == 'north' else 0                                                     # barge boards follow the hip
    if left:
        for y in range(ys0, y1 + 1): c.put(0, y, R('wood')[3]); c.put(1, y, R('wood')[2])
        if part == 'north':
            for y in range(0, 5): c.put(5 - y, y, R('wood')[3])
    if right:
        for y in range(ys0, y1 + 1): c.put(19, y, R('wood')[0]); c.put(18, y, R('wood')[1])
        if part == 'north':
            for y in range(0, 5): c.put(14 + y, y, R('wood')[1])
    return c

# ---------------------------------------------------------------- furniture and stations
def _spr(c, ox, oy, dark): c.outline_inside(dark); refine(c); return (c, ox, oy)

def table(fam='wood', w=24, top=None):
    r = R(fam); h = 18; c = Canvas(w, h); n = len(r); t = top or r
    c.rect(1, 3, w - 2, 7, t[min(len(t) - 2, 3)]); c.hline(1, w - 2, 3, t[min(len(t) - 1, 4)]); c.hline(1, w - 2, 9, t[1]); c.hline(1, w - 2, 10, t[0])
    c.hline(4, 12, 6, t[2]); c.hline(14, w - 5, 7, t[2])
    for x in (3, w - 5): c.rect(x, 11, 2, 6, r[1]); c.put(x, 11, r[0])
    return _spr(c, w // 2, 16, r[0])

def chair(fam='wood', seat=None):
    r = R(fam); c = Canvas(12, 20)
    c.rect(2, 1, 8, 9, r[2]); c.hline(2, 9, 1, r[4]); c.hline(3, 8, 4, r[1]); c.hline(3, 8, 7, r[1])     # ladder back
    sr = seat or r; c.rect(1, 10, 10, 4, sr[min(3, len(sr) - 2)]); c.hline(1, 10, 10, sr[-1]); c.hline(1, 10, 13, r[1])
    c.rect(2, 14, 2, 5, r[1]); c.rect(8, 14, 2, 5, r[1])
    return _spr(c, 6, 18, r[0])

def bed(fam='wood', blanket='flower_b', side=False):
    r = R(fam); b = R(blanket); cv = R('canvas')
    if side:   # head to the left, seen from the side
        c = Canvas(30, 20)
        c.rect(1, 3, 3, 15, r[2]); c.hline(1, 3, 3, r[4]); c.rect(26, 7, 3, 11, r[2]); c.hline(26, 28, 7, r[4])
        c.rect(4, 7, 22, 9, r[3]); c.rect(4, 6, 22, 7, b[1]); c.hline(11, 25, 6, b[2]); c.rect(4, 6, 7, 6, cv[5]); c.hline(4, 10, 11, cv[3]); c.hline(4, 25, 13, r[1]); c.hline(4, 25, 15, r[1])
        for x in (14, 20): c.vline(x, 7, 12, b[0])
        return _spr(c, 15, 18, r[0])
    c = Canvas(20, 30)
    c.rect(1, 1, 18, 6, r[2]); c.hline(1, 18, 1, r[4]); c.hline(2, 17, 4, r[1])                # headboard
    c.rect(2, 7, 16, 19, b[1]); c.rect(3, 7, 14, 6, cv[5]); c.hline(3, 16, 12, cv[3]); c.vline(3, 7, 11, cv[4])  # pillow
    c.hline(2, 17, 13, b[2]); c.hline(2, 17, 14, b[0]); c.vline(2, 13, 25, b[2]); c.vline(17, 13, 25, b[0])
    for y in (18, 22):
        for x in range(4, 16, 4): c.put(x, y, b[2]); c.put(x + 1, y, b[2])                     # quilt stitch
    c.rect(1, 26, 18, 3, r[2]); c.hline(1, 18, 26, r[3]); c.hline(1, 18, 28, r[1])
    return _spr(c, 10, 28, r[0])

def shelf(books=False):
    r = R('wood'); c = Canvas(20, 30)
    c.rect(1, 1, 18, 28, r[1]); c.vline(1, 1, 28, r[3]); c.vline(18, 1, 28, r[0]); c.hline(1, 18, 1, r[4])
    for sy in (9, 17, 25): c.hline(2, 17, sy, r[3]); c.hline(2, 17, sy + 1, r[0])
    rng = random.Random(5 if books else 6)
    cols = [R('berry')[1], R('flower_b')[1], R('moss')[1], R('canvas')[3], R('flower_p')[1], R('flower_y')[1]]
    for y1 in (8, 16, 24):
        x = 3
        while x < 16:
            if books:
                h = rng.randint(4, 6); col = rng.choice(cols); c.rect(x, y1 - h + 1, 2, h, col); c.put(x, y1 - h + 1, PAL.i('canvas', 5)); x += 2 + (rng.random() < .2)
            else:
                if rng.random() < .45: c.rect(x, y1 - 2, 3, 3, rng.choice([R('metal')[2], R('canvas')[3], R('dirt')[3]])); c.put(x, y1 - 2, R('canvas')[4])
                x += 4
    return _spr(c, 10, 28, r[0])

def cabinet():
    r = R('wood'); mt = R('metal'); c = Canvas(20, 24)
    c.rect(1, 2, 18, 20, r[2]); c.hline(0, 19, 1, r[4]); c.hline(0, 19, 2, r[3])
    for x0 in (2, 11):
        c.rect(x0, 4, 7, 16, r[3]); c.hline(x0, x0 + 6, 4, r[4]); c.vline(x0 + 6, 4, 19, r[1]); c.rect(x0 + 2, 7, 3, 9, r[2])
    c.put(8, 12, mt[3]); c.put(11, 12, mt[3]); c.hline(1, 18, 22, r[1])
    return _spr(c, 10, 22, r[0])

def chest(fam='wood', strap='metal', big=False):
    r = R(fam); m = R(strap); W = 22 if big else 18; c = Canvas(W, 16)
    c.rect(1, 1, W - 2, 6, r[3]); c.hline(2, W - 3, 1, r[4]); c.hline(1, W - 2, 6, r[1])       # lid
    c.rect(1, 7, W - 2, 7, r[2]); c.hline(1, W - 2, 7, r[1]); c.hline(1, W - 2, 10, r[1])
    for x in (3, W - 5): c.rect(x, 1, 2, 13, m[2]); c.vline(x, 1, 13, m[3])
    c.rect(W // 2 - 2, 5, 4, 4, R('lantern_glass')[1]); c.put(W // 2 - 1, 7, m[0])
    return _spr(c, W // 2, 14, r[0])

def crate():
    r = R('wood'); c = Canvas(16, 16)
    c.rect(1, 2, 14, 12, r[3]); c.hline(1, 14, 2, r[4])
    for y in (6, 10): c.hline(1, 14, y, r[1])
    c.line(2, 13, 13, 3, r[2]); c.rect(1, 2, 2, 12, r[2]); c.rect(13, 2, 2, 12, r[1])
    return _spr(c, 8, 14, r[0])

def rug(col1, col2):
    a, b = R(col1), R(col2); cv = R('canvas'); c = Canvas(32, 22)
    c.rect(1, 1, 30, 20, a[1]); c.rect(3, 3, 26, 16, b[1]); c.rect(5, 5, 22, 12, a[1]); c.rect(7, 7, 18, 8, cv[3])
    for x in range(8, 24, 4):
        c.put(x, 10, a[2]); c.put(x + 1, 11, a[2]); c.put(x + 2, 10, a[2])
    for x in range(1, 31, 2): c.put(x, 0, cv[4]); c.put(x, 21, cv[4])                          # fringe
    return (c, 16, 21)

def floor_lamp():
    w = R('wood'); g = R('lantern_glass'); cv = R('canvas'); c = Canvas(12, 30)
    c.rect(5, 12, 2, 16, w[2]); c.vline(5, 12, 27, w[3]); c.hline(3, 8, 28, w[1]); c.hline(4, 7, 27, w[2])
    c.poly([(4, 1), (8, 1), (11, 11), (1, 11)], cv[3]); c.rect(4, 4, 4, 7, g[2]); c.rect(5, 5, 2, 4, g[3]); c.hline(1, 10, 11, cv[1]); c.hline(4, 7, 1, cv[4])
    return _spr(c, 6, 28, w[0])

def table_lantern():
    m = R('metal'); g = R('lantern_glass'); c = Canvas(10, 14)
    c.rect(3, 0, 4, 2, m[2]); c.rect(2, 2, 6, 2, m[1]); c.rect(2, 4, 6, 7, g[1]); c.rect(3, 5, 4, 5, g[2]); c.rect(4, 6, 2, 3, g[3]); c.vline(2, 4, 10, m[1]); c.vline(7, 4, 10, m[0]); c.rect(1, 11, 8, 2, m[1]); c.hline(1, 8, 11, m[2])
    return (c, 5, 12)

def spore_jar():
    i, g = R('ice'), R('glowshroom'); c = Canvas(10, 14)
    c.rect(3, 0, 4, 2, R('wood')[3]); c.rect(1, 2, 8, 10, i[2]); c.vline(1, 3, 10, i[3]); c.rect(2, 4, 6, 7, g[1]); c.rect(3, 5, 3, 4, g[2]); c.put(4, 6, R('moonlight')[2]); c.hline(2, 7, 12, i[0])
    return _spr(c, 5, 12, i[0])

def potted():
    f = R('fern'); d = R('dirt'); c = Canvas(16, 20)
    for (x0, y0, x1, y1) in ((8, 11, 2, 4), (8, 11, 5, 1), (8, 11, 11, 1), (8, 11, 14, 5), (8, 11, 3, 8), (8, 11, 13, 9)):
        c.line(x0, y0, x1, y1, f[2]); c.line(x0 + 1, y0, x1 + 1, y1 + 1, f[3]); c.put(x1, y1, f[4])
    c.poly([(3, 11), (13, 11), (12, 18), (4, 18)], d[3]); c.hline(2, 13, 11, d[4]); c.hline(2, 13, 12, d[3]); c.vline(4, 13, 17, d[4]); c.vline(11, 13, 17, d[2]); c.hline(4, 11, 18, d[1])
    return _spr(c, 8, 18, d[0])

def painting():
    w = R('wood'); c = Canvas(14, 12)
    c.rect(0, 0, 14, 12, w[3]); c.hline(0, 13, 0, w[4]); c.hline(0, 13, 11, w[1]); c.rect(2, 2, 10, 8, R('water')[4])
    c.rect(2, 6, 10, 4, R('grass')[3]); c.poly([(3, 7), (6, 3), (9, 7)], R('oak')[2]); c.put(10, 3, R('flower_y')[2]); c.hline(2, 11, 9, R('grass')[2])
    return (c, 7, 11)

def wall_shelf():
    w = R('wood'); c = Canvas(16, 12)
    c.rect(1, 8, 14, 2, w[3]); c.hline(1, 14, 8, w[4]); c.hline(1, 14, 10, w[0]); c.put(3, 11, w[1]); c.put(12, 11, w[1])
    c.rect(3, 3, 3, 5, R('metal')[2]); c.put(3, 3, R('metal')[3]); c.rect(8, 5, 2, 3, R('berry')[1]); c.rect(11, 4, 2, 4, R('ice')[2]); c.put(11, 4, R('ice')[4])
    return (c, 8, 11)

def stove():
    st = R('stone'); f = R('fire'); m = R('metal'); c = Canvas(22, 30)
    c.rect(8, 0, 6, 8, m[1]); c.vline(8, 0, 7, m[2]); c.hline(7, 14, 0, m[3])                  # flue
    c.rect(1, 8, 20, 20, st[2]); c.hline(1, 20, 8, st[4]); c.hline(1, 20, 9, st[3])
    for y in (14, 20, 26): c.hline(1, 20, y, st[1])
    c.rect(5, 15, 12, 10, m[0]); c.rect(6, 17, 10, 7, f[1]); c.rect(8, 19, 6, 5, f[2]); c.rect(10, 21, 2, 3, f[3]); c.hline(5, 16, 15, m[2])
    return _spr(c, 11, 28, st[0])

def counter():
    w = R('wood'); st = R('stone'); c = Canvas(24, 20)
    c.rect(1, 2, 22, 5, st[3]); c.hline(1, 22, 2, st[5]); c.hline(1, 22, 6, st[1])
    c.rect(2, 7, 20, 11, w[2]); c.vline(12, 7, 17, w[0]); c.rect(4, 9, 6, 7, w[3]); c.rect(14, 9, 6, 7, w[3]); c.put(9, 12, R('metal')[3]); c.put(15, 12, R('metal')[3])
    c.rect(15, 0, 4, 3, R('metal')[2]); c.put(15, 0, R('metal')[3]); c.ellipse(6, 1.5, 3, 1.3, R('canvas')[4])
    return _spr(c, 12, 18, w[0])

def workbench():
    w = R('wood'); m = R('metal'); c = Canvas(32, 24)
    c.rect(1, 7, 30, 6, w[3]); c.hline(1, 30, 7, w[4]); c.hline(1, 30, 12, w[1]); c.hline(5, 14, 9, w[2]); c.hline(16, 27, 10, w[2])
    for x in (3, 26): c.rect(x, 13, 3, 9, w[2]); c.vline(x, 13, 21, w[3])
    c.hline(5, 26, 17, w[1]); c.hline(5, 26, 18, w[0])
    c.line(5, 5, 11, 2, w[3]); c.rect(10, 1, 4, 3, m[2]); c.put(10, 1, m[3])                    # hammer on the top
    c.rect(20, 3, 8, 4, m[1]); c.hline(20, 27, 3, m[3]); c.rect(22, 1, 2, 2, m[2])              # vise
    c.rect(8, 15, 3, 2, m[2]); c.put(18, 15, R('canvas')[4]); c.put(19, 15, R('canvas')[3])
    return _spr(c, 16, 22, w[0])

def stone_station():
    st = R('stone'); w = R('wood'); m = R('metal'); c = Canvas(32, 24)
    c.ellipse(16, 15, 14, 7, st[2]); c.ellipse(15, 13, 12, 5, st[3]); c.ellipse(13, 12, 7, 2.5, st[4]); c.hline(5, 26, 20, st[1])
    c.rect(10, 7, 8, 6, st[4]); c.hline(10, 17, 7, st[5]); c.vline(17, 7, 12, st[2]); c.hline(10, 17, 12, st[2]); c.line(12, 9, 15, 11, st[1])   # block being cut
    c.line(22, 12, 27, 7, w[3]); c.rect(26, 5, 3, 3, m[2]); c.line(20, 8, 23, 4, m[3])           # mallet, chisel
    return _spr(c, 16, 21, st[0])

def wood_station():
    w = R('wood'); m = R('metal'); c = Canvas(32, 24)
    for x in (4, 22):
        for k in range(2): c.line(x + k, 21, x + 3 + k, 11, w[2 - k]); c.line(x + 6 + k, 21, x + 3 + k, 11, w[2 - k])   # sawhorses, two pixels thick
    c.rect(1, 7, 30, 5, w[4]); c.hline(1, 30, 7, R('canvas')[4]); c.hline(1, 30, 11, w[2]); c.ellipse(30, 9, 1.5, 2.5, R('canvas')[3]); c.put(30, 9, w[2])
    c.poly([(13, 3), (24, 3), (24, 7), (13, 6)], m[3]); c.hline(13, 24, 7, m[1])                 # saw in the cut
    c.rect(24, 1, 4, 5, w[3]); c.put(25, 2, w[1])
    for x in (10, 13, 20): c.put(x, 22, R('canvas')[4]); c.put(x + 1, 22, R('canvas')[3])        # sawdust
    return _spr(c, 16, 22, w[0])

def furnace():
    st = R('stone'); f = R('fire'); m = R('metal'); c = Canvas(28, 32)
    c.rect(11, 0, 6, 7, st[2]); c.hline(10, 17, 0, st[4]); c.vline(11, 0, 6, st[3])
    c.ellipse(14, 17, 12, 13, st[2]); c.ellipse(11, 13, 7, 8, st[3]); c.rect(2, 25, 24, 5, st[2]); c.hline(2, 25, 29, st[1])
    for (x, y) in ((6, 10), (13, 7), (20, 12), (5, 20), (21, 21), (12, 26)): c.hline(x, x + 4, y, st[1])
    c.ellipse(14, 22, 6, 5, st[0]); c.rect(8, 22, 12, 5, st[0]); c.ellipse(14, 24, 4, 3, f[1]); c.ellipse(14, 25, 2.5, 2, f[2]); c.put(14, 25, f[3]); c.hline(7, 20, 16, m[2])
    return _spr(c, 14, 30, st[0])

def adv_bench():
    m = R('metal'); w = R('wood_grey'); r = R('metal_rust'); c = Canvas(32, 26)
    c.rect(1, 8, 30, 6, w[3]); c.hline(1, 30, 8, w[4]); c.hline(1, 30, 13, w[0]); c.rect(2, 14, 28, 10, m[1]); c.vline(2, 14, 23, m[2])
    for x0 in (4, 12, 20): c.rect(x0, 16, 7, 3, m[2]); c.hline(x0, x0 + 6, 16, m[3]); c.put(x0 + 3, 17, m[0]); c.rect(x0, 20, 7, 3, m[2]); c.put(x0 + 3, 21, m[0])
    c.ellipse(8, 5, 3.5, 3.5, r[2]); c.ellipse(8, 5, 1.3, 1.3, r[0]); [c.put(x, y, r[1]) for x, y in ((8, 0), (3, 5), (13, 5))]
    c.rect(18, 2, 8, 6, m[2]); c.rect(19, 3, 6, 3, R('glowshroom')[1]); c.put(20, 4, R('glowshroom')[2]); c.line(14, 7, 18, 6, r[2])
    return _spr(c, 16, 24, m[0])

def garden():
    w = R('wood'); d = R('dirt'); g = R('grass'); c = Canvas(30, 18)
    c.rect(1, 3, 28, 13, w[2]); c.hline(1, 28, 3, w[4]); c.hline(1, 28, 15, w[1]); c.rect(3, 5, 24, 9, d[1]); c.hline(3, 26, 7, d[2]); c.hline(3, 26, 11, d[2])
    for x in range(5, 26, 5):
        for y in (6, 10): c.put(x, y, g[3]); c.put(x + 1, y - 1, g[4]); c.put(x - 1, y - 1, g[4])
    return _spr(c, 15, 16, w[0])

def barricade():
    w = R('wood'); m = R('metal'); c = Canvas(30, 22)
    c.line(2, 19, 26, 5, w[3]); c.line(2, 20, 26, 6, w[1]); c.line(3, 5, 27, 19, w[4]); c.line(3, 6, 27, 20, w[1]); c.rect(4, 12, 22, 3, w[2]); c.hline(4, 25, 12, w[3]); c.put(14, 12, m[3]); c.put(15, 13, m[2])
    return _spr(c, 15, 20, w[0])

def spikes():
    w = R('wood'); c = Canvas(30, 18); c.rect(1, 13, 28, 3, w[1]); c.hline(1, 28, 13, w[2])
    for x in range(3, 27, 6):
        c.line(x, 14, x + 3, 2, w[4]); c.line(x + 1, 14, x + 4, 2, w[2]); c.put(x + 3, 1, R('canvas')[4]); c.line(x + 5, 14, x + 3, 6, w[1])
    return _spr(c, 15, 16, w[0])

def platform():
    w = R('wood'); c = Canvas(32, 48)
    for x in (3, 26): c.rect(x, 18, 3, 28, w[2]); c.vline(x, 18, 45, w[3])
    c.line(6, 44, 25, 24, w[1]); c.line(26, 44, 7, 24, w[1])
    c.rect(1, 13, 30, 5, w[3]); c.hline(1, 30, 13, w[4]); c.hline(1, 30, 18, w[0]); [c.vline(x, 13, 17, w[1]) for x in range(4, 30, 5)]
    c.hline(1, 30, 3, w[3]); c.hline(1, 30, 4, w[1]); [c.rect(x, 3, 2, 10, w[2]) for x in (1, 15, 29)]
    for y in range(22, 46, 4): c.hline(13, 18, y, w[3]); c.put(13, y + 1, w[0])
    c.vline(13, 18, 46, w[1]); c.vline(18, 18, 46, w[1])
    return _spr(c, 16, 46, w[0])

def torch():
    w = R('wood'); f = R('fire'); m = R('metal'); c = Canvas(10, 28)
    c.rect(4, 9, 2, 18, w[2]); c.vline(4, 9, 26, w[3]); c.rect(3, 7, 4, 3, m[1]); c.hline(3, 6, 7, m[2])
    c.poly([(5, 0), (8, 6), (2, 6)], f[1]); c.poly([(5, 2), (7, 6), (3, 6)], f[2]); c.put(5, 5, f[3])
    return (c, 5, 26)

def steps():
    st = R('stone'); c = Canvas(20, 10); c.rect(2, 1, 16, 4, st[3]); c.hline(2, 17, 1, st[5]); c.hline(2, 17, 4, st[1]); c.rect(0, 5, 20, 4, st[3]); c.hline(0, 19, 5, st[4]); c.hline(0, 19, 8, st[1])
    return _spr(c, 10, 9, st[0])

def post():
    w = R('wood'); c = Canvas(10, 34); c.rect(3, 2, 4, 30, w[2]); c.vline(3, 2, 31, w[3]); c.vline(6, 2, 31, w[1]); c.rect(1, 0, 8, 3, w[3]); c.hline(1, 8, 0, w[4]); c.rect(2, 31, 6, 2, w[1])
    return _spr(c, 5, 32, w[0])

def furniture():
    w = R('wood'); ms = R('metal'); st = R('stone'); cv = R('canvas')
    return {
        'workbench': workbench(), 'stone_station': stone_station(), 'wood_station': wood_station(), 'furnace': furnace(), 'adv_bench': adv_bench(),
        'chest': chest(), 'chest_big': chest(big=True), 'crate': crate(),
        'bed_rustic': bed('wood', 'moss'), 'bed_rustic_side': bed('wood', 'moss', side=True), 'bed_cottage': bed('canvas', 'flower_p'), 'bed_cottage_side': bed('canvas', 'flower_p', side=True),
        'table_rustic': table('wood'), 'table_stone': table('wood', top=st), 'table_industrial': table('metal', top=R('wood_grey')), 'table_cottage': table('wood', top=cv),
        'chair_rustic': chair('wood'), 'chair_cottage': chair('wood', seat=R('flower_b')), 'shelf': shelf(), 'bookshelf': shelf(True), 'cabinet': cabinet(),
        'rug_woven': rug('berry', 'flower_y'), 'rug_moss': rug('moss', 'flower_b'), 'floor_lamp': floor_lamp(), 'table_lantern': table_lantern(), 'potted_fern': potted(), 'spore_jar': spore_jar(),
        'painting': painting(), 'wall_shelf': wall_shelf(), 'stove': stove(), 'counter': counter(), 'garden_bed': garden(),
        'barricade': barricade(), 'spikes': spikes(), 'watch_platform': platform(), 'torch_post': torch(), 'stone_steps': steps(), 'roof_support': post(),
    }

def all_sprites():
    """name -> (Canvas, ox, oy)"""
    out = {}
    for mat in WALLS:
        for mask in range(16): out[f'wall_{mat}_{mask}'] = (wall(mat, mask), 0, 38)
        for k in ('window', 'door_closed', 'door_open'): out[f'{k}_{mat}'] = (wall(mat, E | W_, k), 0, 38)
    for mask in range(16): out[f'fence_{mask}'] = (fence(mask), 0, 19)
    for k in ('gate_closed', 'gate_open', 'rgate_closed', 'rgate_open'): out[k] = (fence(0, k), 0, 19)
    for mat in ('wood', 'reinforced', 'stone'):
        for mask in range(16):
            if not mask & N: out[f'fnd_{mat}_{mask}'] = (foundation(mat, mask), 0, 0)
    for k in ('plank', 'flag', 'tile'): out[f'floor_{k}'] = (floor(k), 0, 0)
    for mat in ('thatch', 'shingle', 'slate'):
        for part in ROOF_PARTS:
            for l in (0, 1):
                for r in (0, 1): out[f'roof_{mat}_{part}_{l}{r}'] = (roof(mat, part, l, r), 2, 0)
    out.update(furniture())
    return out
