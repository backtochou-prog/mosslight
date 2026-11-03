"""Festival decorations. Every piece is hand-built in the world palette, grounded (contact shadows through the normal
placement path) and meant to be composed around one focal point per festival, never strewn."""
from __future__ import annotations
import math, random
from .canvas import Canvas, refine
from .palette import PAL
from .objects import Sprite
R = PAL.ramp
def _s(name, c, ox, oy, tags=('prop', 'ysort'), shadow=None, contact=None, outline=True, dark=None):
    if outline: c.outline_inside(dark if dark is not None else R('wood')[0]); refine(c)
    return Sprite(name, c, ox, oy, shadow=shadow, tags=tags, contact=contact)

# ---------------------------------------------------------------- SPRING: The Awakening
def blossom_crown():
    """A crown of white and pale-pink blossom that sits over the lone rowan for one day a year."""
    rng = random.Random(14); c = Canvas(44, 40); fw, fp, rw = R('flower_w'), R('flower_p'), R('rowan')
    for (x, y, rx, ry) in ((22, 22, 15, 10), (12, 18, 9, 7), (32, 18, 9, 7), (22, 10, 11, 8), (16, 28, 8, 5), (29, 28, 8, 5)):
        c.ellipse(x, y, rx, ry, rw[2]); c.ellipse(x - 1, y - 2, rx * .8, ry * .7, rw[3])
    for _ in range(170):
        a = rng.random() * 6.28; r = rng.random() ** .6; x = 22 + math.cos(a) * 18 * r; y = 19 + math.sin(a) * 14 * r
        if c.get(int(x), int(y)) == 0: continue
        up = y < 19; c.put(int(x), int(y), fw[2] if up else fw[1]); c.put(int(x) + 1, int(y), fp[2] if rng.random() < .3 else fw[1 if up else 0])
    for _ in range(14): x, y = rng.randint(6, 38), rng.randint(6, 34); c.put(x, y, R('flower_y')[2])
    return _s('blossom_crown', c, 22, 47, outline=True, dark=rw[0])
def blossom_small():
    rng = random.Random(15); c = Canvas(30, 26); fw, fp, bi = R('flower_w'), R('flower_p'), R('birch')
    for (x, y, rx, ry) in ((15, 15, 11, 8), (9, 10, 6, 5), (21, 9, 6, 5)): c.ellipse(x, y, rx, ry, bi[2])
    for _ in range(90):
        x, y = rng.randint(2, 28), rng.randint(2, 24)
        if c.get(x, y): c.put(x, y, fw[2] if y < 14 else fp[1]); c.put(x + 1, y, fp[2] if rng.random() < .4 else fw[1])
    return _s('blossom_small', c, 15, 30, dark=bi[0])
def flower_drift(v):
    """A dense drift of wildflowers in two or three colours, thinning at its edges, like a real meadow patch."""
    rng = random.Random(70 + v); c = Canvas(56, 26); g = R('grass'); fam = [('flower_w', 'flower_y'), ('flower_p', 'flower_w'), ('flower_b', 'flower_w')][v % 3]
    for _ in range(140):
        x, y = rng.gauss(28, 12), rng.gauss(13, 5.5)
        if not (1 <= x < 55 and 2 <= y < 25): continue
        x, y = int(x), int(y); c.put(x, y + 1, g[2]); c.put(x, y, g[4])
        if rng.random() < .55: f = R(fam[0] if rng.random() < .65 else fam[1]); c.put(x, y - 1, f[2]); c.put(x + 1, y - 1, f[1]); c.put(x, y - 2, f[1])
    return Sprite(f'flower_drift_{v}', c, 28, 14, shadow=None, tags=('ground',))
def leaf_carpet(v):
    rng = random.Random(60 + v); c = Canvas(48, 22); lf = R('leaf_litter'); cols = [lf[2], lf[3], R('berry')[1], R('flower_y')[1]]
    c.ellipse(24, 12, 20, 7, lf[1]); c.ellipse(22, 11, 15, 5, lf[2])                     # a drift with a body, not confetti
    for _ in range(70):
        x, y = rng.gauss(24, 9), rng.gauss(11, 3.5)
        if 1 <= x < 47 and 1 <= y < 21: col = cols[rng.randint(0, 3)]; c.put(int(x), int(y), col); c.put(int(x) + 1, int(y) + 1, lf[1])
    return Sprite(f'leaf_carpet_{v}', c, 24, 12, shadow=None, tags=('ground',))
def petals(v):
    rng = random.Random(30 + v); c = Canvas(48, 20); fw, fp = R('flower_w'), R('flower_p')
    for _ in range(46):
        x, y = rng.gauss(24, 10), rng.gauss(10, 4)
        if 0 <= x < 47 and 0 <= y < 19: c.put(int(x), int(y), fw[2] if rng.random() < .6 else fp[2]); 
        if rng.random() < .3 and 0 <= x + 1 < 48 and 0 <= y < 20: c.put(int(x) + 1, int(y), fw[1])
    return Sprite(f'petals_{v}', c, 24, 10, shadow=None, tags=('ground',))
def flower_arch():
    """Two bent hazel poles tied at the top, woven with blossom and green, over the path into the meadow."""
    c = Canvas(64, 56); w, mo, fw, fy, fp = R('wood'), R('moss'), R('flower_w'), R('flower_y'), R('flower_p')
    for k in range(64):
        t = k / 63; x = 4 + 56 * t; y = 52 - 46 * math.sin(t * math.pi)
        for d in range(3): c.put(int(x), int(y) + d, w[2 + (d == 0)])
        c.put(int(x), int(y) - 1, mo[2 if k % 3 else 1]); c.put(int(x), int(y) - 2, mo[1])
        if k % 4 == 0: c.put(int(x), int(y) - 3, [fw[2], fy[2], fp[2]][k // 4 % 3]); c.put(int(x) + 1, int(y) - 3, [fw[1], fy[1], fp[1]][k // 4 % 3])
    for x in (4, 60): c.rect(x - 1, 34, 3, 21, w[2]); c.vline(x - 1, 34, 54, w[3]); c.hline(x - 2, x + 2, 54, w[0])
    for (x, y) in ((8, 40), (56, 40), (10, 30), (54, 30)): c.ellipse(x, y, 3, 2.5, mo[2]); c.put(x, y - 1, fw[2])
    for k, x in enumerate((22, 32, 42)): c.vline(x, 9 + (k == 1) * -2, 18, R('berry')[1] if k != 1 else fy[1]); c.put(x, 19, fw[2])   # ribbons hanging from the top
    return _s('flower_arch', c, 32, 55, shadow=(26, 3, 3, 0), contact=(3, 1))
def wish_post():
    c = Canvas(14, 32); w = R('wood'); c.rect(6, 4, 3, 27, w[2]); c.vline(6, 4, 30, w[4]); c.hline(5, 9, 30, w[0]); c.rect(5, 2, 5, 3, w[3])
    for k, col in enumerate((R('berry')[1], R('flower_y')[1], R('flower_b')[1], R('flower_p')[1])):
        for t in range(8 + k * 2): c.put(9 + (t // 3) % 2 + (k % 2), 5 + k + t, col)
    c.put(2, 8, R('flower_w')[2]); c.line(3, 8, 6, 9, R('rope')[1])
    return _s('wish_post', c, 7, 30, shadow=(4, 1, 1, 1), contact=(2, .8))
def paper_lantern_line():
    """A line of paper lanterns on cord between two posts."""
    c = Canvas(72, 40); w, lg, rp = R('wood'), R('lantern_glass'), R('rope')
    for x in (2, 69): c.rect(x - 1, 6, 3, 33, w[2]); c.vline(x - 1, 6, 38, w[4]); c.hline(x - 2, x + 2, 38, w[0])
    for k in range(66): x = 2 + k; y = 7 + int(9 * math.sin(k / 66 * math.pi)); c.put(x, y, rp[1])
    for k, x in enumerate((14, 26, 38, 50, 61)):
        y = 7 + int(9 * math.sin((x - 2) / 66 * math.pi)) + 1; col = (lg, R('flower_p'), lg, R('flower_w'), lg)[k]
        c.vline(x, y, y + 1, rp[0]); c.ellipse(x, y + 5, 3, 3.6, col[1]); c.ellipse(x - .5, y + 4, 2, 2.4, col[2]); c.hline(x - 1, x + 1, y + 2, w[1]); c.hline(x - 1, x + 1, y + 9, w[1])
    return _s('paper_lantern_line', c, 36, 39, shadow=(30, 2, 3, 0))

# ---------------------------------------------------------------- SUMMER: The Firefly Evening
def lily_lantern(v):
    """A small lantern riding a lily pad: only ever on the water."""
    c = Canvas(20, 20); li, lg, w, fp = R('lily'), R('lantern_glass'), R('wood'), R('flower_p')
    c.ellipse(10, 15, 9, 3.8, li[1]); c.ellipse(9, 14, 7, 2.8, li[2]); c.ellipse(8, 13.5, 4, 1.4, li[3]); c.put(16, 15, 0); c.put(17, 14, 0); c.put(15, 16, 0)
    for k in range(5): c.put(4 + k * 3, 15 - (k % 2), fp[1 + (k % 2)])
    c.ellipse(10, 7, 4.2, 5, lg[1 + v % 2]); c.ellipse(9, 6, 2.4, 3.4, lg[2]); c.put(9, 5, lg[3]); c.hline(7, 13, 2, w[1]); c.hline(7, 13, 12, w[1]); c.put(10, 1, w[2])
    return Sprite(f'lily_lantern_{v}', _s('x', c, 10, 17, outline=True, dark=li[0]).c, 10, 17, shadow=None, tags=('ysort', 'water'))
def reed_lantern():
    c = Canvas(12, 30); r, lg, w = R('reed'), R('lantern_glass'), R('wood')
    for (x, h, k) in ((3, 24, 1), (6, 28, 2), (8, 20, 3)): c.line(x, 29, x + (k - 2), 29 - h, r[k])
    c.line(6, 3, 9, 6, w[1]); c.rect(8, 7, 3, 5, lg[2]); c.put(8, 7, lg[3]); c.hline(8, 10, 12, w[0])
    return _s('reed_lantern', c, 6, 29, dark=r[0])
def firefly_jar():
    c = Canvas(10, 12); ic, ff, w = R('ice'), R('firefly'), R('wood')
    c.rect(2, 2, 6, 9, ic[1]); c.rect(3, 3, 4, 7, ic[2]); c.vline(2, 3, 9, ic[3]); c.rect(3, 0, 4, 2, w[2]); c.put(4, 5, ff[0]); c.put(6, 8, ff[0]); c.put(3, 8, ff[0])
    return _s('firefly_jar', c, 5, 11, dark=ic[0])

# ---------------------------------------------------------------- AUTUMN: The Harvest of Forgotten Things
def leaf_garland():
    c = Canvas(72, 36); w, lf, rp = R('wood'), R('leaf_litter'), R('rope')
    for x in (2, 69): c.rect(x - 1, 4, 3, 31, w[2]); c.vline(x - 1, 4, 34, w[4]); c.hline(x - 2, x + 2, 34, w[0])
    for k in range(66):
        x = 2 + k; y = 5 + int(8 * math.sin(k / 66 * math.pi)); c.put(x, y, rp[1])
        if k % 3 == 0: col = [lf[3], R('berry')[1], lf[2], R('flower_y')[1]][k // 3 % 4]; c.put(x, y + 1, col); c.put(x + 1, y + 2, col); c.put(x, y + 2, lf[1]); c.put(x + 1, y + 1, col)
    return _s('leaf_garland', c, 36, 35, shadow=(30, 2, 3, 0))
def bonfire():
    c = Canvas(40, 40); st, w, f, em = R('stone'), R('wood'), R('fire'), R('ember')
    for k in range(14): a = k / 14 * 6.28; x, y = 20 + math.cos(a) * 15, 31 + math.sin(a) * 6; c.ellipse(x, y, 3, 2, st[2]); c.put(int(x) - 1, int(y) - 1, st[4])
    for (x0, y0, x1, y1) in ((9, 33, 22, 18), (31, 33, 18, 18), (14, 35, 28, 20), (26, 35, 13, 20), (20, 36, 20, 16)): c.line(x0, y0, x1, y1, w[1]); c.line(x0 + 1, y0, x1 + 1, y1, w[3])
    for k in range(60):
        rng = random.Random(k); x = 20 + rng.gauss(0, 4); y = 28 - abs(rng.gauss(0, 9)); c.put(int(x), int(y), f[min(3, int((28 - y) / 4))])
    c.ellipse(20, 30, 6, 2, em[1])
    return _s('bonfire', c, 20, 36, contact=(14, 2), dark=st[0])
def leaf_heap():
    rng = random.Random(9); c = Canvas(28, 14); lf = R('leaf_litter')
    c.ellipse(14, 9, 13, 5, lf[1]); c.ellipse(13, 7, 10, 4, lf[2])
    for _ in range(40): x, y = rng.randint(3, 25), rng.randint(3, 12); c.put(x, y, [lf[3], R('berry')[1], R('flower_y')[1], lf[2]][rng.randint(0, 3)])
    c.put(20, 6, R('metal')[3]); c.put(21, 6, R('metal')[2])          # something glints in it
    return _s('leaf_heap', c, 14, 13, contact=(11, 1.5), dark=lf[0])
def mushroom_ring():
    c = Canvas(48, 20); sh, ss = R('shroom'), R('shroom_stem')
    for k in range(11):
        a = k / 11 * 6.28; x, y = 24 + math.cos(a) * 20, 10 + math.sin(a) * 7
        c.vline(int(x), int(y), int(y) + 2, ss[1]); c.hline(int(x) - 1, int(x) + 1, int(y) - 1, sh[2]); c.put(int(x), int(y) - 2, sh[3]); c.put(int(x) - 1, int(y) - 1, sh[1])
    return Sprite('mushroom_ring', c, 24, 12, shadow=None, tags=('ground',))
def forgotten_table():
    """A long slab on two stumps where the clearing lays out what the year turned up."""
    c = Canvas(48, 26); w, g = R('wood'), R('wood_grey')
    for x in (8, 38): c.rect(x - 4, 12, 8, 12, w[2]); c.ellipse(x, 12, 4, 1.4, R('canvas')[3]); c.vline(x - 4, 12, 23, w[4])
    c.rect(1, 8, 46, 4, g[2]); c.hline(1, 46, 8, g[4]); c.hline(1, 46, 11, g[0])
    items = [(6, R('metal_rust')[2], 3, 3), (13, R('flower_y')[2], 2, 2), (19, R('ice')[3], 3, 4), (27, R('canvas')[4], 4, 3), (35, R('berry')[1], 2, 2), (41, R('metal')[3], 3, 2)]
    for (x, col, ww, hh) in items: c.rect(x, 8 - hh, ww, hh, col); c.put(x, 8 - hh, R('flower_w')[2])
    return _s('forgotten_table', c, 24, 24, shadow=(20, 2, 2, 1), contact=(18, 1.5))
def gourd_lantern():
    c = Canvas(12, 12); o, f = R('fire'), R('lantern_glass')
    c.ellipse(6, 7, 5, 4, R('berry')[1]); c.ellipse(5, 6, 3.5, 2.6, R('fire')[1]); c.rect(5, 1, 2, 3, R('moss')[1])
    c.put(4, 6, f[3]); c.put(7, 6, f[3]); c.hline(4, 7, 9, f[2])
    return _s('gourd_lantern', c, 6, 11, dark=R('wood')[0])

# ---------------------------------------------------------------- WINTER: The Silent Tide
def ice_lantern():
    c = Canvas(10, 14); ic, lg = R('ice'), R('lantern_glass')
    c.rect(1, 3, 8, 10, ic[2]); c.rect(2, 4, 2, 8, ic[3]); c.vline(8, 4, 12, ic[1]); c.hline(1, 8, 3, ic[4]); c.rect(4, 6, 2, 4, lg[2]); c.put(4, 6, lg[3]); c.hline(1, 8, 13, R('snow')[3])
    return _s('ice_lantern', c, 5, 13, dark=ic[0])
def tide_ring():
    """Stones and snow banked around the ice hole, with a ring of small lights."""
    c = Canvas(40, 20); sn, st = R('snow'), R('stone')
    for k in range(16): a = k / 16 * 6.28; x, y = 20 + math.cos(a) * 16, 10 + math.sin(a) * 7; c.ellipse(x, y, 2.6, 1.6, sn[3] if k % 3 else st[2]); c.put(int(x) - 1, int(y) - 1, sn[4])
    return Sprite('tide_ring', c, 20, 10, shadow=None, tags=('ground',))
def all_sprites():
    out = [blossom_crown(), flower_arch(), wish_post(), paper_lantern_line(), reed_lantern(), firefly_jar(), leaf_garland(), bonfire(), leaf_heap(), mushroom_ring(), forgotten_table(), gourd_lantern(), ice_lantern(), tide_ring()]
    out += [petals(v) for v in range(3)] + [lily_lantern(v) for v in range(2)] + [leaf_carpet(v) for v in range(3)] + [blossom_small()] + [flower_drift(v) for v in range(3)]
    return {s.name: s for s in out}
