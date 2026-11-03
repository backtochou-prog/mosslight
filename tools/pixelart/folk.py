"""The first inhabitants of MOSSlight: six intelligent, non-human, non-hostile beings. World sprites use the world
palette (so dusk, night and seasons grade them like everything else, and lantern glass and eyes glow by themselves);
portraits use the plate palette from fish.py, like the field-book illustrations. Each has its own body plan."""
from __future__ import annotations
import math
import numpy as np
from .canvas import Canvas, refine
from .palette import PAL
from . import fish as FP
R = PAL.ramp
def _fin(c, ox, oy, dark, ref=True):
    c.outline_inside(dark)
    if ref: refine(c)
    return (c, ox, oy)
def shade_ellipse(c, cx, cy, rx, ry, ramp, lo=1, hi=None, light=(-.45, -.55)):
    """Round form lit from the upper left: rank follows the surface normal, so masses read as volumes."""
    hi = len(ramp) - 1 if hi is None else hi
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            dx, dy = (x + .5 - cx) / rx, (y + .5 - cy) / ry; d = dx * dx + dy * dy
            if d > 1: continue
            nz = math.sqrt(1 - d); l = max(0, -(dx * light[0] + dy * light[1]) * .8 + nz * .55)
            c.put(x, y, ramp[max(0, min(len(ramp) - 1, int(lo + (hi - lo) * l + .2)))])

# ------------------------------------------------------------------ world sprites (face the viewer; mirrored for left)
def ebb(f):
    """Keeper of the pond: a broad, old, wet head under a driftwood mask, duckweed fronds for gills. Only the head rises."""
    c = Canvas(34, 22); sk, mo, wg, w = R('lily'), R('moss'), R('wood_grey'), R('water'); bob = [0, 1, 0, 0][f % 4]; sub = f == 4
    y0 = 6 + bob + (5 if sub else 0)
    if not sub:
        for side in (-1, 1):                                   # frond-gills, three plumes a side
            for k in range(3):
                bx = 17 + side * (8 + k * 2); by = y0 + 3 + k * 2
                for t in range(6): c.put(bx + side * t, by - t // 2 + (k == 1) * (t // 4), mo[2 if t < 3 else 1]); c.put(bx + side * t, by - t // 2 + 1, mo[1])
                c.put(bx + side * 6, by - 3, R('grass')[5])
        shade_ellipse(c, 17, y0 + 6, 10, 6.5, sk, 0, 3)       # head
        c.ellipse(17, y0 + 11, 9, 2.5, sk[0])
    else:
        shade_ellipse(c, 17, y0 + 4, 9, 3.5, sk, 0, 2)
    # the mask: a driftwood plate, grain lines, two worn eye holes with pale light inside
    my = y0 + (1 if sub else 2)
    c.ellipse(17, my + 2, 7, 3.6, wg[2]); c.hline(11, 23, my + 1, wg[3]); c.hline(12, 22, my, wg[4]); c.hline(12, 22, my + 4, wg[1])
    for x in (13, 16, 19, 21): c.put(x, my + 3, wg[1])
    for ex in (14, 20): c.rect(ex - 1, my + 2, 2, 2, wg[0]); c.put(ex, my + 2, R('eyes')[0])
    if not sub:
        c.ellipse(13, y0 + 1, 3.2, 1.6, R('lily')[2]); c.ellipse(13, y0 + .5, 2.2, .9, R('lily')[3]); c.put(14, y0, R('flower_p')[2]); c.put(13, y0, R('flower_p')[1])   # lily pad crown, one flower
        c.hline(13, 21, y0 + 9, sk[0]); c.put(17, y0 + 10, sk[1])                     # mouth line under the mask
    # the water: a wake ring where the body meets the surface
    yy = y0 + (8 if sub else 11)
    for x in range(4, 31):
        e = abs(x - 17) / 13
        c.put(x, yy + int(e * 2), w[5] if (x + f) % 4 else w[6]); c.put(x, yy + 1 + int(e * 2), w[3])
    return _fin(c, 17, 21, sk[0])
def pip(f):
    """The little forager: a chestnut burr on twig legs under one enormous leaf; a moss satchel stuffed with finds."""
    c = Canvas(16, 18); wd, fe, mo = R('wood'), R('fern'), R('moss'); st = [0, 1, 0, -1][f % 4]; up = 1 if f % 2 else 0
    for lx, s in ((6, st), (9, -st)): c.line(lx, 13 - up, lx + s, 16, wd[1]); c.put(lx + s, 17, wd[0]); c.put(lx + s + 1, 17, wd[0])
    shade_ellipse(c, 8, 10 - up, 5, 4.6, wd, 1, 5)
    for x, y in ((5, 7), (8, 6), (11, 7), (6, 12), (10, 12)): c.put(x, y - up, wd[5])     # burr spines catching light
    c.rect(5, 9 - up, 2, 2, wd[0]); c.rect(9, 9 - up, 2, 2, wd[0]); c.put(5, 9 - up, R('shroom_stem')[2]); c.put(9, 9 - up, R('shroom_stem')[2])   # eyes
    c.put(7, 12 - up, wd[1]); c.put(8, 12 - up, wd[1])
    c.line(3, 11 - up, 1, 13 - up - st, wd[2]); c.line(13, 11 - up, 15, 12 - up + st, wd[2])                     # twig arms
    c.rect(11, 11 - up, 4, 4, mo[1]); c.hline(11, 14, 11 - up, mo[3]); c.put(13, 12 - up, R('flower_y')[2]); c.put(12, 13 - up, R('shroom')[2])   # satchel with a flower and a mushroom
    for x in range(0, 16):                                    # the leaf hat, veined, tip curling
        y = 4 - up - int(2.4 * math.sin((x + .5) / 16 * math.pi)); c.vline(x, y, 5 - up, fe[2 if x < 6 else 3]); c.put(x, y, fe[4])
    c.hline(1, 14, 5 - up, fe[1]); c.line(2, 4 - up, 13, 3 - up, fe[1]); c.put(15, 3 - up, fe[4]); c.vline(8, 0, 2 - up + 1, wd[2])
    return _fin(c, 8, 17, wd[0])
def wick(f):
    """The lantern keeper: tall, wrapped in its own folded moth wings like a coat, a paper lantern where a head would be."""
    c = Canvas(18, 34); wg, cv, wd = R('wood_grey'), R('canvas'), R('wood'); bob = [0, 1, 1, 0][f % 4]; y = bob
    for k in range(17):                                        # the wing-cloak, wider at the hem, dust scales banded
        hw = 3 + k * .32; yy = 12 + k + y
        for x in range(int(9 - hw), int(9 + hw) + 1):
            t = (x - (9 - hw)) / (2 * hw); r = 3 if t < .35 else 2 if t < .7 else 1
            if k in (6, 7) and abs(x - 9) > 2: r = 4
            c.put(x, yy, wg[r])
    for ex in (5, 13): c.put(ex, 22 + y, R('flower_y')[1]); c.put(ex, 23 + y, wg[0])  # eye-spots low on the wings
    c.vline(9, 14 + y, 28 + y, wg[1]); c.hline(4, 14, 29 + y, wg[0])
    for x in (6, 9, 12): c.put(x, 30 + y, wg[1 if x != 9 else 2])                          # ragged hem
    c.line(3, 17 + y, 5, 22 + y, cv[3]); c.line(15, 17 + y, 13, 22 + y, cv[3])          # pale thin hands holding the cloak shut
    lg = R('lantern_glass'); pulse = f % 4 == 2
    c.rect(6, 3 + y, 7, 8, lg[2 if not pulse else 3]); c.rect(7, 4 + y, 2, 6, lg[3]); c.vline(12, 4 + y, 10 + y, lg[1])   # the lantern head
    for yy in (3, 6, 10): c.hline(6, 12, yy + y, wd[1])
    c.put(9, 6 + y, R('fire')[3]); c.put(9, 7 + y, R('fire')[2]); c.put(10, 7 + y, R('fire')[1])
    c.hline(7, 11, 2 + y, wd[2]); c.put(9, 1 + y, wd[3])
    for s in (-1, 1):                                          # feathered antennae
        for t in range(5): c.put(9 + s * (2 + t), 1 + y - t // 2, cv[4]); c.put(9 + s * (2 + t), 2 + y - t // 2, cv[2] if t % 2 else 0)
    return _fin(c, 9, 31, wg[0])
def burl(f):
    """The rootbound elder: a great stump with a bark face, a moss beard, a sapling of its own growing from the crown."""
    c = Canvas(40, 36); wd, mo, ok = R('wood'), R('moss'), R('oak')
    for x0, dx in ((6, -5), (11, -3), (28, 3), (33, 5), (20, 0)):                         # roots
        c.line(x0, 30, x0 + dx, 34, wd[1]); c.line(x0 + 1, 30, x0 + dx + 1, 34, wd[2])
    for x in range(7, 34):                                     # trunk with deep vertical grooves
        t = (x - 7) / 26; r = 4 if t < .25 else 3 if t < .55 else 2 if t < .85 else 1
        c.vline(x, 12, 31, wd[r])
        if x % 4 == 0: c.vline(x, 13 + (x * 3) % 5, 30, wd[max(0, r - 2)])
    c.ellipse(20, 12, 13.5, 3.6, wd[3]); c.ellipse(20, 12, 10, 2.4, R('canvas')[3]); c.ellipse(20, 12, 6, 1.4, R('canvas')[4]); c.ellipse(20, 12, 2.5, .6, R('canvas')[2])   # cut rings on top
    c.vline(24, 2, 11, wd[2]); c.vline(25, 3, 10, wd[3])
    for (x, y, r) in ((21, 3, 3), (27, 5, 2.6), (24, 1, 2.2)): shade_ellipse(c, x, y, r, r * .8, ok, 2, 6)   # the sapling's crown
    eo = {0: 1, 1: 1, 2: 0, 3: .5}[f % 4]
    for ex in (15, 25):                                        # knothole eyes
        c.ellipse(ex, 18, 2.4, 2 * max(.35, eo), wd[0])
        if eo: c.put(ex, 18, R('glowshroom')[2]); c.put(ex - 1, 17, wd[1])
    c.line(15, 23, 25, 23, wd[0]); c.put(20, 24, wd[0]); c.hline(16, 24, 22, wd[2])       # the mouth: a long split in the bark
    sw = [0, 1, 0, -1][f % 4]
    for x in range(12, 29):                                    # moss beard, hanging lower in the middle
        L = 3 + int(5 * math.sin((x - 12) / 16 * math.pi)); c.vline(x + (sw if L > 5 else 0) * (x % 2), 25, 25 + L, mo[1 + (x % 3 == 0) + (x % 5 == 0)])
    for x, y in ((9, 15), (30, 19), (11, 27)): c.ellipse(x, y, 2.2, 1.2, mo[2]); c.put(x, y - 1, mo[3])
    return _fin(c, 20, 33, wd[0])
def tessel(f):
    """The mechanical wanderer: a rusted survey dome on three jointed legs, one big lens, a scrap of cloth for a flag."""
    c = Canvas(22, 26); mt, ru, ice = R('metal'), R('metal_rust'), R('ice'); st = [0, 1, 0, -1][f % 4]
    for lx, ph in ((5, st), (11, -st), (16, st)):              # three legs, knees up
        c.line(11, 15, lx - 1, 19 + ph // 2, mt[2]); c.line(lx - 1, 19 + ph // 2, lx + ph, 24, mt[1]); c.put(lx - 1, 19 + ph // 2, ru[2]); c.hline(lx + ph - 1, lx + ph + 1, 24, mt[0])
    shade_ellipse(c, 11, 11, 8, 6.2, ru, 0, 2); c.ellipse(11, 8, 7, 3.2, mt[3]); c.ellipse(10, 7, 4.5, 1.6, mt[3]); c.hline(4, 18, 13, mt[0]); c.put(6, 9, ru[2]); c.put(16, 11, ru[0])   # dome with a painted band
    for x in range(4, 19, 3): c.put(x, 14, mt[1])                                         # rivets
    c.ellipse(11, 11, 3.6, 3.2, mt[0]); c.ellipse(11, 11, 2.7, 2.4, ice[1]); c.ellipse(11.5, 11.5, 1.6, 1.4, R('water')[0])   # the lens
    lens = {0: (10, 10), 1: (10, 10), 2: (12, 10), 3: (10, 11)}[f % 4]; c.put(*lens, ice[4]); c.put(lens[0] + 1, lens[1], ice[3])
    c.vline(16, 0, 6, mt[2]); c.rect(17, 0, 4, 3, R('berry')[1]); c.hline(17, 20, 0, R('berry')[2])                      # antenna and flag
    c.ellipse(7, 6, 2.6, 1.1, R('moss')[2]); c.put(6, 5, R('moss')[3]); c.put(8, 5, R('flower_w')[2])                     # moss and a flower growing on it
    c.line(3, 13, 0, 16, mt[2]); c.put(0, 17, mt[3]); c.put(1, 17, mt[3])                                                  # tool arm
    return _fin(c, 11, 25, mt[0])
def lull(f):
    """The dreaming creature: a curled drift of mist and pollen, many small eyes closed, a long tail of fog behind."""
    c = Canvas(34, 22); mi, mo = R('mist'), R('moonlight')
    wob = lambda a: math.sin(a + f * 1.57)
    for k in range(14):                                        # the tail, thinning, waving
        x = 3 + k * 1.1; y = 14 + 3 * wob(k * .55); r = 2.6 - k * .14
        c.ellipse(x, y, max(.8, r), max(.6, r * .7), mi[1 if k % 3 else 0])
    for (x, y, rx, ry, rk) in ((20, 12, 9, 6.5, 1), (23, 10, 7, 5, 2), (19, 9, 5, 3.5, 2), (25, 8, 3.5, 2.5, 2)): c.ellipse(x, y + wob(x) * .6, rx, ry, mi[rk])
    for (x, y) in ((17, 7), (22, 6), (26, 7), (20, 5)): c.put(x, y, mi[2]); c.put(x + 1, y - 1, mo[2])
    awake = f == 4
    for (x, y) in ((19, 11), (23, 10), (26, 12), (21, 14)):   # small eyes: closed arcs, open glints when it wakes
        if awake: c.put(x, y, R('eyes')[0]); c.put(x + 1, y, mo[0])
        else: c.hline(x, x + 1, y, mo[0])
    for (x, y) in ((12, 7), (29, 15), (16, 17), (31, 9), (9, 11)): c.put(x, y + int(wob(x)), R('flower_y')[2])            # drifting pollen
    return (c, 20, 20)
WORLD = dict(ebb=(ebb, 5), pip=(pip, 4), wick=(wick, 4), burl=(burl, 4), tessel=(tessel, 4), lull=(lull, 5))

# ------------------------------------------------------------------ portraits: 48x48 busts on a wash of their own place
P = FP.ci
def _plate(): c = Canvas(48, 48); return c
def _wash(c, fam, r0=2):
    """A full plate of the character's own place: lighter behind the head, darker at the corners."""
    for y in range(48):
        for x in range(48):
            d = math.hypot(x - 24, y - 20) / 30
            c.put(x, y, P(fam, max(0, r0 - (1 if d > .95 else 0) + (1 if d < .6 else 0) + (1 if d < .3 and (x + y) % 2 == 0 else 0))))
def pshade(c, cx, cy, rx, ry, fam, lo, hi, light=(-.45, -.6)):
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            dx, dy = (x + .5 - cx) / rx, (y + .5 - cy) / ry; d = dx * dx + dy * dy
            if d > 1: continue
            nz = math.sqrt(1 - d); l = max(0, -(dx * light[0] + dy * light[1]) * .8 + nz * .5); c.put(x, y, P(fam, lo + (hi - lo) * l + .2))
def p_outline(c, fam, skip_bg=True):
    """Dark selective outline around the figure only, not around the wash."""
    pass
def portrait_ebb(e):
    c = _plate(); _wash(c, 'teal', 1)
    for side in (-1, 1):                                       # frond gills fanning behind the head
        for k in range(5):
            for t in range(15):
                x = 24 + side * (11 + t); y = 20 + k * 3 - int(t * .55) + int(math.sin(t * .7 + k) * 1.3); c.put(x, y, P('moss', 3 if t < 7 else 2)); c.put(x, y + 1, P('moss', 1))
            c.put(24 + side * 26, 20 + k * 3 - 8, P('lume', 4))
    pshade(c, 24, 27, 17, 13, 'olive', 1, 4.6)                  # broad, old head
    for k in range(7): c.put(12 + k * 4, 33 + k % 2, P('olive', 0))                         # wrinkles along the jaw
    for y in range(37, 48):                                     # the pond line cuts across the chest
        for x in range(48): c.put(x, y, P('aqua', 1 + ((x + y // 2) % 7 == 0) + (y == 37)))
    for x in range(48):
        if x % 6 < 4: c.put(x, 37, P('ivory', 5))
    for y in range(14, 30):                                     # the driftwood mask: a worn oval, grain running round it
        for x in range(10, 39):
            d = ((x - 24) / 14) ** 2 + ((y - 22) / 8.2) ** 2
            if d > 1 or (d > .86 and (x * 7 + y) % 5 == 0): continue
            g = int(abs(math.sin(math.hypot(x - 24, (y - 22) * 1.6) * .7)) * 2.4); c.put(x, y, P('bone', 1 + g - (x > 32) - (y > 27) + (y < 17)))
    eyes = {'calm': 1.6, 'glad': 1.0, 'troubled': 2.3}[e]
    for ex in (18, 30):
        c.ellipse(ex, 22, 3.4, eyes * 1.2, P('black', 0)); c.put(ex, 22, P('glow', 5)); c.put(ex + 1, 22, P('glow', 3))
        if e == 'troubled': c.line(ex - 3, 18 + (ex > 24), ex + 3, 18 + (ex < 24), P('bone', 0))
    for s_, x0 in ((-1, 16), (1, 32)):                          # barbels: long, slow, old
        for t in range(12): c.put(x0 + s_ * int(t * .3), 30 + t, P('olive', 2 if t < 6 else 1))
    mouth = {'calm': 0, 'glad': -1, 'troubled': 1}[e]
    c.line(17, 32, 24, 32 + mouth, P('olive', 0)); c.line(24, 32 + mouth, 31, 32, P('olive', 0))
    pshade(c, 15, 11, 6.5, 3, 'moss', 2, 5); c.put(16, 9, P('rose', 4)); c.put(17, 9, P('rose', 5)); c.put(15, 10, P('rose', 3)); c.put(17, 10, P('rose', 3))
    return c
def portrait_pip(e):
    c = _plate(); _wash(c, 'moss', 2)
    pshade(c, 24, 31, 13, 12, 'amber', 1, 5)
    for (x, y) in ((14, 24), (19, 21), (27, 20), (33, 23), (15, 34), (34, 33), (24, 19)): c.put(x, y, P('amber', 5)); c.put(x, y + 1, P('amber', 1))
    for x in range(2, 46):                                     # the great leaf hat
        y = 16 - int(8 * math.sin((x - 1) / 45 * math.pi)) + (2 if x > 40 else 0)
        for yy in range(y, 20): c.put(x, yy, P('moss', 3 if x < 18 else 4 if yy > y else 5))
    c.line(4, 18, 44, 14, P('moss', 1)); [c.line(10 + k * 7, 17 - k // 2, 13 + k * 7, 11 - k // 2, P('moss', 2)) for k in range(5)]
    eh = {'calm': 4, 'glad': 3, 'troubled': 5}[e]
    for ex in (18, 30):
        c.rect(ex - 2, 26, 5, eh, P('black', 1)); c.rect(ex - 1, 26, 2, 2, P('ivory', 5)); c.put(ex + 1, 26 + eh - 2, P('glow', 3))
    if e == 'troubled': c.line(15, 23, 20, 25, P('amber', 0)); c.line(33, 23, 28, 25, P('amber', 0))
    if e == 'glad': c.hline(21, 27, 35, P('amber', 0)); c.put(20, 34, P('amber', 0)); c.put(28, 34, P('amber', 0)); c.rect(22, 36, 5, 1, P('crimson', 3))
    elif e == 'troubled': c.rect(23, 35, 3, 2, P('amber', 0))
    else: c.hline(22, 26, 35, P('amber', 0))
    c.rect(36, 36, 9, 9, P('moss', 2)); c.hline(36, 44, 36, P('moss', 4)); c.put(39, 38, P('lemon', 4)); c.put(42, 39, P('crimson', 4)); c.put(40, 40, P('ivory', 5))
    return c
def portrait_wick(e):
    c = _plate(); _wash(c, 'indigo', 0)
    br = {'calm': 3, 'glad': 4, 'troubled': 2}[e]
    for y in range(48):                                        # the glow on the night around it, dithered, wider when it is glad
        for x in range(48):
            d = math.hypot(x - 24, (y - 16) * 1.1) / (16 + br * 2)
            if d < 1 and (x + y) % 2 == 0 and d > .55: c.put(x, y, P('indigo', 2))
            elif d < .7 and (x * 3 + y) % 3 == 0: c.put(x, y, P('indigo', 3))
    for y in range(27, 48):                                    # the wing cloak, folded shut
        hw = 8 + (y - 27) * .75
        for x in range(int(24 - hw), int(24 + hw) + 1):
            t = (x - 24 + hw) / (2 * hw); c.put(x, y, P('umber', 4 if t < .3 else 3 if t < .65 else 2))
        if y % 5 == 0: c.hline(int(24 - hw) + 2, int(24 + hw) - 2, y, P('umber', 2))
    for (x, y) in ((12, 39), (36, 39)): c.ellipse(x, y, 3.2, 2.6, P('black', 2)); c.ellipse(x, y, 1.8, 1.4, P('gold', 4)); c.put(x - 1, y - 1, P('lemon', 5))
    c.vline(24, 29, 47, P('umber', 1)); c.line(17, 33, 21, 38, P('flesh', 4)); c.line(31, 33, 27, 38, P('flesh', 3))          # thin hands at the fold
    for y in range(6, 27):                                     # paper lantern: a rounded body with curved ribs
        hw = 9.5 * math.sqrt(max(0, 1 - ((y - 16) / 10.5) ** 2))
        for x in range(int(24 - hw), int(24 + hw) + 1):
            t = (x - 24 + hw) / (2 * hw + .01); c.put(x, y, P('gold', min(5, br + (1 if .25 < t < .5 else 0) - (1 if t > .82 else 0))))
    for k, y in enumerate((9, 13, 17, 21, 24)):
        hw = 9.5 * math.sqrt(max(0, 1 - ((y - 16) / 10.5) ** 2))
        for x in range(int(24 - hw), int(24 + hw) + 1): c.put(x, y + (1 if abs(x - 24) < hw * .5 else 0), P('amber', 2))
    c.rect(19, 4, 11, 3, P('umber', 1)); c.hline(19, 29, 4, P('umber', 3)); c.rect(20, 26, 9, 2, P('umber', 1))
    fl = {'calm': 3, 'glad': 5, 'troubled': 2}[e]
    for k in range(fl): c.put(24 + (k % 2) * (1 if k > 2 else 0), 19 - k, P('ember', 5 if k == fl - 1 else 4))
    c.put(23, 19, P('ember', 3)); c.put(25, 19, P('ember', 3))
    for s_ in (-1, 1):                                          # feathered antennae curling out of the cap
        for t in range(16):
            x = 24 + s_ * (4 + t); y = 4 - int(math.sin(t / 15 * math.pi) * 4) + t // 5; c.put(x, y, P('flesh', 4))
            if t % 2: c.put(x, y + 1, P('flesh', 2)); c.put(x - s_, y - 1, P('flesh', 3))
    return c
def portrait_burl(e):
    c = _plate(); _wash(c, 'olive', 1)
    for x in range(4, 44):                                    # the trunk face fills the plate
        t = (x - 4) / 40; r = 4 if t < .25 else 3 if t < .55 else 2 if t < .85 else 1
        c.vline(x, 12, 47, P('umber', r))
        if x % 4 == 0: c.vline(x, 14 + (x * 7) % 9, 47, P('umber', max(0, r - 2)))
    c.ellipse(24, 12, 20, 4, P('umber', 4)); c.ellipse(24, 12, 15, 2.8, P('bone', 3)); c.ellipse(24, 12, 9, 1.6, P('bone', 4))
    for (x, y, r) in ((28, 4, 4), (34, 6, 3.5), (31, 1, 3)): pshade(c, x, y, r, r * .8, 'moss', 2, 5)
    c.vline(31, 5, 11, P('umber', 2))
    eo = {'calm': 1.6, 'glad': 1.1, 'troubled': 2.4}[e]
    for ex in (16, 32):
        c.ellipse(ex, 23, 4, eo * 1.4, P('black', 1)); c.ellipse(ex, 23 - eo * .6, 4.5, .9, P('umber', 4))
        c.put(ex, 23, P('lume', 5)); c.put(ex + 1, 23, P('lume', 3))
    if e == 'troubled': c.line(11, 18, 19, 20, P('umber', 0)); c.line(37, 18, 29, 20, P('umber', 0))
    my = {'calm': 0, 'glad': -1, 'troubled': 1}[e]
    c.line(14, 31, 24, 31 - my, P('black', 1)); c.line(24, 31 - my, 34, 31, P('black', 1))
    for x in range(10, 39):
        L = 6 + int(9 * math.sin((x - 10) / 28 * math.pi)); c.vline(x, 34, min(47, 34 + L), P('moss', 1 + (x % 3 == 0) + (x % 4 == 0)))
    return c
def portrait_tessel(e):
    c = _plate(); _wash(c, 'steel', 1)
    pshade(c, 24, 30, 18, 15, 'rust', 0, 4)
    c.ellipse(24, 20, 16, 6, P('steel', 3)); c.ellipse(21, 18, 9, 2.6, P('steel', 4)); c.hline(7, 41, 33, P('char', 1))
    for x in range(8, 41, 4): c.put(x, 35, P('char', 2))
    c.ellipse(24, 29, 9.5, 9, P('char', 0)); c.ellipse(24, 29, 8, 7.5, P('steel', 1)); c.ellipse(24, 29, 6, 5.6, P('aqua', 1))
    pr = {'calm': 3, 'glad': 4.5, 'troubled': 1.8}[e]; c.ellipse(24.5, 29.5, pr, pr, P('ink', 1)); c.put(21, 26, P('ivory', 5)); c.put(22, 26, P('aqua', 5)); c.put(21, 27, P('aqua', 4))
    if e == 'glad':
        for k in range(3): c.put(14 + k * 2, 42, P('lume', 5)); c.put(30 + k * 2, 42, P('lume', 5))
    if e == 'troubled': c.put(38, 25, P('ember', 5)); c.put(38, 26, P('ember', 4))
    c.vline(37, 2, 14, P('steel', 3)); c.rect(38, 2, 8, 5, P('crimson', 3)); c.hline(38, 45, 2, P('crimson', 4))
    pshade(c, 14, 15, 5, 2.4, 'moss', 2, 5); c.put(13, 13, P('ivory', 5)); c.put(16, 13, P('lemon', 4))
    return c
def portrait_lull(e):
    c = _plate(); _wash(c, 'violet', 1)
    for (x, y) in ((6, 9), (41, 7), (9, 41), (44, 33), (3, 26), (36, 44), (28, 4)): c.put(x, y, P('lemon', 5)); c.put(x + 1, y + 1, P('lemon', 3))
    # curled body: a crescent of mist around a sleeping centre, tail spiralling inward
    for y in range(48):
        for x in range(48):
            d1 = math.hypot(x - 24, y - 26) / 18; d2 = math.hypot(x - 28, y - 23) / 9.5
            if d1 < 1 and d2 > 1:
                edge = d1 > .86 and (x + y) % 2
                if not edge: c.put(x, y, P('moon', 2 + (d1 < .7) + (y < 22 and x < 30) + (d1 < .4)))
    for t in range(60):                                        # tail curling into the hollow
        a = t / 60 * 5.2; r = 9 - t * .12; x = 28 + math.cos(a) * r; y = 23 + math.sin(a) * r * .9
        c.ellipse(x, y, max(.7, 2.4 - t * .03), max(.6, 1.8 - t * .025), P('moon', 3 if t % 7 else 4))
    head = (14, 24); pshade(c, head[0], head[1], 8, 7, 'moon', 2, 5)
    eyes = [(10, 22), (14, 20), (18, 23), (12, 27), (17, 28)]
    for i, (x, y) in enumerate(eyes):
        if e == 'glad': c.rect(x, y, 2, 2, P('ink', 1)); c.put(x, y, P('glow', 5))
        elif e == 'calm': c.hline(x, x + 1, y + 1, P('indigo', 2)) if i % 2 else (c.rect(x, y, 2, 2, P('ink', 1)), c.put(x, y, P('glow', 5)))
        else: c.put(x, y + 1, P('indigo', 1)); c.put(x + 1, y, P('indigo', 1))
    for k in range(9): c.put(33 + (k * 5) % 9, 12 + (k * 7) % 22, P('lemon', 4))       # pollen it carries
    return c
PORTRAITS = dict(ebb=portrait_ebb, pip=portrait_pip, wick=portrait_wick, burl=portrait_burl, tessel=portrait_tessel, lull=portrait_lull)
EXPR = ['calm', 'glad', 'troubled']
def outline_figure(c, bg_fams):
    """Selective dark outline where the figure meets its wash (not where the wash meets nothing)."""
    a = c.a; fam = np.vectorize(lambda i: FP.FAM_OF[i][0] if i else '')(a); fig = (a != 0) & ~np.isin(fam, bg_fams)
    p = np.pad(fig, 1); edge = fig & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
    for y, x in zip(*np.nonzero(edge)):
        f, r = FP.FAM_OF[a[y, x]]; a[y, x] = P(f, max(0, r - 2))
    return c
