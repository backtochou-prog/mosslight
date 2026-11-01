"""Original creature art. Language of the forest: bodies overtaken by moss, fungus and bark;
asymmetry; the eyes are never a pair of red dots. Faces right; the game mirrors for left.
Emissive families (glowshroom, moonlight, eyes) brighten by themselves at night."""
from __future__ import annotations
import math, random
import numpy as np
from .canvas import Canvas, refine
from .palette import PAL
R = PAL.ramp
def _fin(c, ox, oy, dark): c.outline_inside(dark); refine(c); return (c, ox, oy)
def _lump(c, cx, cy, rx, ry, r, top=None):
    """Shaded mass: shadow base, mid, lit upper-left cap."""
    n = len(r); c.ellipse(cx, cy, rx, ry, r[1]); c.ellipse(cx - rx * .12, cy - ry * .15, rx * .8, ry * .75, r[min(2, n - 1)]); c.ellipse(cx - rx * .3, cy - ry * .4, rx * .42, ry * .35, top if top else r[min(3, n - 1)])

def wanderer(f):
    """Hunched mushroom-carrier: a dead thing walked by the fungus on its back. Lopsided, one long arm."""
    c = Canvas(26, 32); b, sh, st, mo = R('wood_grey'), R('shroom'), R('shroom_stem'), R('moss')
    sw = [0, 1, 0, -1][f]; bob = [0, 1, 0, 1][f]; y = bob
    c.rect(10 + sw, 22 + y, 3, 8 - y, b[1]); c.rect(15 - sw, 22 + y, 3, 8 - y, b[2]); c.hline(9 + sw, 13 + sw, 29, b[0]); c.hline(15 - sw, 19 - sw, 29, b[1])   # legs
    _lump(c, 13, 16 + y, 7, 8, b); c.rect(8, 18 + y, 2, 3, mo[1]); c.put(16, 21 + y, mo[0]); c.put(10, 21 + y, mo[2])      # torso with moss
    c.line(18, 13 + y, 21, 22 + y + sw, b[1]); c.line(19, 13 + y, 22, 22 + y + sw, b[2]); c.rect(21, 22 + y + sw, 3, 3, st[1])        # long arm
    c.ellipse(17, 10 + y, 4, 3.5, st[1]); c.put(20, 10 + y, R('eyes')[0]); c.put(18, 12 + y, b[0]); c.hline(18, 20, 12 + y, b[0])     # sunken head, one pale eye
    _lump(c, 10, 8 + y, 8, 5, sh); c.rect(8, 11 + y, 5, 3, st[0]); c.put(6, 7 + y, st[2]); c.put(10, 5 + y, st[2]); c.put(13, 8 + y, st[2])    # fungal cap
    _lump(c, 4, 13 + y, 3, 2, sh); c.put(3, 15 + y, st[1])
    return _fin(c, 13, 30, b[0])

def stalker(f, crouch=False):
    """Long-limbed and low, more spider than wolf: bark plates, a row of three cold eyes on a narrow head."""
    c = Canvas(38, 20); b, bk = R('pine'), R('wood_grey'); y = 2 if crouch else 0; sw = [0, 2, 0, -2][f]
    for (x0, s) in ((9, sw), (13, -sw), (25, -sw), (29, sw)):     # jointed legs: knees above the body line
        c.line(x0, 9 + y, x0 - 3, 4 + y, bk[2]); c.line(x0 + 1, 9 + y, x0 - 2, 4 + y, bk[1]); c.line(x0 - 3, 4 + y, x0 - 4 + s, 18, bk[2]); c.line(x0 - 2, 4 + y, x0 - 3 + s, 18, bk[1]); c.put(x0 - 3, 3 + y, bk[3])
    c.ellipse(20, 10 + y, 12, 3.6, b[1]); c.ellipse(19, 9 + y, 10, 2.4, b[2])
    for x in range(10, 30, 4): c.put(x, 7 + y, b[4]); c.put(x + 1, 8 + y, b[3])                                                  # dorsal plates
    c.line(9, 10 + y, 2, 7 + y, b[1]); c.put(1, 6 + y, b[2])                                                                       # whip tail
    c.ellipse(33, 9 + y, 4, 2.4, b[1]); c.hline(32, 37, 11 + y, bk[0])
    for x in (33, 35, 36): c.put(x, 8 + y, R('glowshroom')[2])
    return _fin(c, 20, 18, b[0])

def burrower(f):
    """f 0 mound, 1 cracking, 2 half out, 3 fully out: a ringed grub with a petal mouth."""
    c = Canvas(34, 30); d, r, s = R('dirt'), R('canvas'), R('berry'); g = R('grass')
    c.ellipse(17, 25, 13 if f else 10, 3.6, d[2]); c.ellipse(16, 24, 10 if f else 8, 2.4, d[3]); c.put(9, 25, R('pebble')[1]); c.put(23, 26, R('pebble')[1]); c.put(13, 24, g[3]); c.put(21, 24, g[4])
    if f == 1:
        c.line(11, 25, 16, 23, d[0]); c.line(16, 23, 21, 26, d[0]); c.put(8, 21, d[3]); c.put(26, 20, d[3])
    if f >= 2:
        top = 13 if f == 2 else 5
        for i, y in enumerate(range(24, top, -4)):
            w = 8 - i // 2; c.ellipse(17, y, w, 3.2, r[2]); c.ellipse(16, y - 1, w - 1.5, 2, r[3]); c.hline(17 - w + 1, 17 + w - 1, y + 2, r[1])
        y = top
        for (dx, dy) in ((-7, -2), (7, -2), (-4, -4), (4, -4)): c.ellipse(17 + dx, y + dy, 2.6, 2, s[1]); c.put(17 + dx, y + dy, s[2])
        c.ellipse(17, y, 5.5, 3, s[0]); c.ellipse(17, y, 3, 1.6, R('wood')[0]); c.put(15, y, R('canvas')[5]); c.put(19, y, R('canvas')[5])       # teeth ring
    return _fin(c, 17, 27, d[0])

def howler(f):
    """Very tall and thin, stilted on two legs, a pale throat sac that swells before the call."""
    c = Canvas(26, 44); b, s = R('bark_birch'), R('flower_p'); sw = [0, 1, 0, -1][f % 4]; sac = f == 4
    c.line(11, 24, 9 + sw, 42, b[1]); c.line(15, 24, 17 - sw, 42, b[1]); c.put(9 + sw, 33, b[2]); c.put(17 - sw, 33, b[2]); c.hline(7 + sw, 11 + sw, 42, b[0]); c.hline(15 - sw, 19 - sw, 42, b[0])
    c.ellipse(13, 18, 4.5, 8, b[1]); c.ellipse(12, 16, 3, 6, b[2])
    for y in (13, 17, 21): c.hline(10, 15, y, b[0])                                                    # ribs through the skin
    c.line(16, 12, 22, 22, b[1]); c.line(10, 12, 5, 24, b[1])                                          # thin arms
    c.ellipse(15, 5, 3.5, 4, b[2]); c.put(16, 3, R('eyes')[0]); c.put(17, 7, b[0]); c.rect(15, 8, 3, 2, b[0])          # narrow skull
    rs = 7 if sac else 3.5; c.ellipse(18, 12, rs, rs * .9, s[1]); c.ellipse(17, 11, rs * .6, rs * .5, s[2]); 
    if sac: c.put(15, 9, PAL.i('flower_w', 2))
    for (x, y) in ((8, 4), (11, 2), (13, 1)): c.line(x, y + 4, x, y, R('wood_grey')[2])               # dead-grass crest
    return _fin(c, 13, 42, b[0])

def brute(f):
    """A boulder that grew shoulders: stone-plated hulk with a young tree rooted in its back."""
    c = Canvas(56, 60); st, mo, w, o = R('ruin'), R('moss'), R('wood'), R('oak'); sw = [0, 1, 0, -1][f % 4]; lift = 5 if f == 4 else 0
    c.rect(16 + sw, 44, 9, 14, st[1]); c.rect(32 - sw, 44, 9, 14, st[2]); c.hline(14 + sw, 26 + sw, 57, st[0]); c.hline(30 - sw, 42 - sw, 57, st[0])    # column legs
    _lump(c, 28, 34, 19, 17, st); _lump(c, 40, 26 - lift, 9, 8, st); _lump(c, 14, 28 - lift, 8, 8, st)                     # chest and shoulders
    c.rect(42, 30 - lift, 8, 18, st[2]); c.rect(47, 44 - lift, 7, 8, st[3]); c.vline(42, 30 - lift, 47 - lift, st[3]); c.rect(6, 32 - lift, 7, 16, st[1]); c.rect(4, 46 - lift, 8, 7, st[2])     # huge arms
    for (x, y, l) in ((18, 26, 6), (30, 38, 7), (22, 44, 5), (36, 28, 4)): c.line(x, y, x + l, y + 2, st[0])               # plate cracks
    c.ellipse(36, 30, 5, 5, st[3]); c.rect(35, 30, 6, 3, st[0]); c.put(36, 31, R('fire')[2]); c.put(39, 31, R('fire')[2]); c.hline(35, 41, 34, st[1])    # brow, ember eyes deep in the head
    for _ in range(1): pass
    rng = random.Random(4)
    for _i in range(18): x, y = rng.randint(14, 42), rng.randint(19, 33); c.put(x, y, mo[rng.choice((0, 1, 1, 2))])         # moss mantle
    c.rect(19, 8, 3, 14, w[2]); c.vline(19, 8, 21, w[3]); _lump(c, 20, 6, 8, 5, o); _lump(c, 14, 10, 4, 3, o)                # sapling on its back
    return _fin(c, 28, 58, st[0])

def luminous(f):
    """A drifting lantern-bell: translucent mantle, hanging threads, a slow core. Beautiful at a distance."""
    c = Canvas(30, 34); g, m, x = R('glowshroom'), R('mist'), R('moonlight'); up = [0, -1, -2, -1][f]; y = 8 + up
    for i, tx in enumerate((7, 11, 15, 19, 23)):
        L = 14 + (i * 7 % 5) + (f + i) % 2; 
        for s in range(L):
            xx = tx + int(round(math.sin((s + f * 2 + i) * .6) * 1.2)); c.put(xx, y + 8 + s, g[0] if s % 3 else g[1])
    c.ellipse(15, y + 2, 11, 8, g[0]); c.ellipse(14, y + 1, 9, 6, g[1]); c.ellipse(15, y + 3, 4.5, 3.5, g[2]); c.put(14, y + 2, x[2]); c.put(15, y + 3, x[2]); c.ellipse(11, y - 2, 3, 1.5, m[2])
    c.rect(4, y + 7, 23, 2, 0); [c.put(x_, y + 8, g[1]) for x_ in range(5, 26, 3)]
    return (c, 15, 32)

def all_sprites():
    o = {}
    for f in range(4): o[f'wanderer_{f}'] = wanderer(f); o[f'stalker_{f}'] = stalker(f); o[f'luminous_{f}'] = luminous(f); o[f'brute_{f}'] = brute(f); o[f'howler_{f}'] = howler(f); o[f'burrower_{f}'] = burrower(f)
    o['stalker_crouch'] = stalker(0, True); o['howler_call'] = howler(4); o['brute_swing'] = brute(4)
    return o
def nodes():
    """Extra night-resource sprites: kind -> state -> (canvas, ox, oy)."""
    out = {}; x, st, g, f, d = R('moonlight'), R('metal'), R('glowshroom'), R('fire'), R('dirt')
    c = Canvas(18, 14); c.poly([(9, 1), (13, 11), (5, 11)], st[1]); c.poly([(14, 5), (16, 11), (11, 11)], st[0]); c.put(8, 4, x[2]); c.put(10, 7, x[2]); c.put(7, 9, x[1]); c.put(14, 8, x[2]); c.hline(3, 15, 12, st[0])
    e = Canvas(18, 14); e.hline(5, 12, 12, st[0]); e.put(7, 11, st[1]); e.put(10, 11, st[1]); out['starshard'] = (c, e, 9, 13)
    c = Canvas(18, 12); w = R('water'); c.poly([(3, 10), (6, 3), (10, 6), (13, 2), (15, 10)], w[0]); c.line(6, 4, 7, 9, w[1]); c.line(13, 3, 12, 9, x[1]); c.put(6, 4, x[2]); c.put(13, 3, x[2]); c.hline(2, 15, 10, R('mud')[0])
    e = Canvas(18, 12); e.hline(4, 13, 10, R('mud')[0]); e.put(8, 9, w[0]); out['nightglass'] = (c, e, 9, 11)
    c = Canvas(18, 12); c.ellipse(9, 8, 7, 3, d[1]); c.ellipse(9, 8, 4, 1.6, R('ember')[1]); c.line(6, 8, 9, 2, f[1]); c.line(9, 2, 12, 7, f[0]); c.line(9, 8, 11, 3, f[1]); c.put(9, 2, f[3]); c.put(4, 9, R('pebble')[1])
    e = Canvas(18, 12); e.ellipse(9, 8, 7, 3, d[1]); e.ellipse(9, 8, 3, 1.3, R('ember')[0]); out['ember_vent'] = (c, e, 9, 11)
    c = Canvas(18, 12); 
    for (px, py, r) in ((5, 8, 2.5), (10, 7, 3), (14, 9, 2)): c.ellipse(px, py, r, r * .7, g[1]); c.put(int(px), int(py) - 1, g[2])
    for (px, py) in ((3, 3), (8, 2), (13, 4), (11, 1)): c.put(px, py, g[2])
    e = Canvas(18, 12); e.ellipse(10, 8, 3, 1.5, g[0]); out['spore_patch'] = (c, e, 9, 10)
    return out
