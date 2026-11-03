"""Far waters: four painted fishing places, one 800x360 indexed scene each, in the world palette so the
day and season tables grade them. Each is composed around one idea, not a recolour of the same pond.
  stream    - a bright broken run crossing a birch wood, boulders in the current, a gravel bar underfoot
  marsh     - tea-black still water, cattail walls, drowned snags, low mist
  lake      - snow peaks mirrored in a cold turquoise bowl, pine line, rock shelf underfoot
  reservoir - a brick vault, columns standing in black water, rust pipes, fungus light, one shaft from a grate
The player stands at (400, 318), back to the viewer. The cast lands at y 170-262."""
from __future__ import annotations
import math, random
import numpy as np
from .canvas import Canvas
from .palette import PAL
R = PAL.ramp; W, H = 800, 360; I = PAL.i
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
def band(c, y0, y1, fam, r0, r1, x0=0, x1=W):
    """Vertical gradient over a ramp, dithered, so large fills never read as flat bands."""
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1); v = r0 + (r1 - r0) * t
        for x in range(x0, x1):
            c.put(x, y, I(fam, int(v + BAYER[y & 3][x & 3] / 16)))
def blob(c, cx, cy, rx, ry, fam, rng, lit=True):
    r = R(fam); n = len(r); c.ellipse(cx, cy, rx, ry, r[max(0, n // 2 - 1)]);
    for _ in range(int(rx * ry / 7) + 3):
        a, q = rng.random() * 6.28, rng.random() ** .6; x, y = cx + math.cos(a) * rx * q * .9, cy + math.sin(a) * ry * q * .9; up = (cy - y) / ry
        k = n // 2 + (1 if up > .1 else -1) + (1 if up > .55 else 0); c.ellipse(x, y, 2 + rng.random() * 3, 1.5 + rng.random() * 2, r[max(0, min(n - 1, k))])
    if lit:
        for _ in range(int(rx / 2)): a = -1.57 + (rng.random() - .5) * 1.8; c.ellipse(cx + math.cos(a) * rx * .72, cy + math.sin(a) * ry * .72, 1.8, 1.1, r[n - 1])
def tree(c, x, base, h, fam, rng, trunk='wood', w=3):
    tr = R(trunk); nt = len(tr); c.rect(x - w // 2, base - h, w, h, tr[1]); c.vline(x - w // 2, base - h, base, tr[min(nt - 1, 3)]); c.hline(x - w // 2 - 1, x + w // 2 + 1, base, tr[0])
    for k in range(3): blob(c, x + rng.randint(-5, 5), base - h - 4 - k * 9, 16 - k * 3, 11 - k * 2, fam, rng)
def reflect(c, y_line, y1, fade=.6, jitter=True):
    """Mirror everything above the water line, thinning with distance: a real reflection of the painted scene."""
    rng = random.Random(9)
    for y in range(y_line, y1):
        dy = y - y_line; src = y_line - dy - 1
        if src < 0: break
        off = int(math.sin(y * .7) * (1 + dy * .03)) if jitter else 0
        for x in range(W):
            t = dy / max(1, y1 - y_line)
            if t > fade or (dy % 3 == 2 and t > .22) or (dy % 2 == 1 and t > .55) or ((x // 17 + dy // 2) % 7 == 0 and t > .35): continue
            s = c.get(min(W - 1, max(0, x + off)), src)
            if s: c.put(x, y, PAL.shade[s])

def stream():
    rng = random.Random(21); c = Canvas(W, H, I('forest', 2)); band(c, 0, 106, 'forest', 1, 3); # wood floor behind
    for x in range(0, W, 27):
        tree(c, x + rng.randint(-8, 8), 78 + rng.randint(-8, 6), 44 + rng.randint(0, 16), 'pine' if rng.random() < .3 else 'oak', rng, 'wood', 3)
    for x in range(14, W, 58):
        tree(c, x + rng.randint(-12, 12), 104 + rng.randint(-4, 6), 58 + rng.randint(0, 14), 'birch', rng, 'bark_birch', 3)
    band(c, 100, 134, 'grass', 2, 4)
    for x in range(0, W, 3):
        y = 132 + int(5 * math.sin(x * .017) + 2 * math.sin(x * .09)); c.rect(x, y, 3, 262 - y, I('water', 3))
    band(c, 140, 270, 'water', 4, 2)
    for x in range(0, W):         # bright broken water along diagonal current lines, baked; moving foam is drawn live
        for y in range(136, 268):
            if (x * 5 + y * 17) % 149 < 4 and (x + y * 7 + (y // 9) * 31) % 41 < 13: c.put(x, y, I('water', 5))
    for x in range(0, W, 2):
        y = 132 + int(5 * math.sin(x * .017) + 2 * math.sin(x * .09)); c.rect(x, y - 3, 2, 3, I('mud', 1)); c.rect(x, y, 2, 1, I('water', 6))
    for (x, y, rx, ry) in [(112, 182, 20, 11), (152, 234, 13, 8), (302, 166, 12, 7), (520, 174, 24, 12), (602, 232, 16, 9), (690, 180, 13, 8), (232, 206, 8, 5), (440, 150, 9, 5), (760, 236, 22, 12)]:
        c.ellipse(x, y + ry - 1, rx + 2, 3, I('water', 1)); c.ellipse(x, y, rx, ry, I('stone', 1)); c.ellipse(x - 1, y - 2, rx * .8, ry * .7, I('stone', 2)); c.ellipse(x - rx * .25, y - ry * .35, rx * .45, ry * .35, I('stone', 4))
        c.ellipse(x + rx * .2, y - ry * .5, rx * .35, ry * .25, I('moss', 2)); c.hline(x - rx, x + rx, y + ry, I('water', 6))
    # gravel bar underfoot, not grass: it is where you actually stand in a stream
    for x in range(0, W):
        y = 262 + int(6 * math.sin(x * .011 + 1) + 3 * math.sin(x * .05)); c.rect(x, y, 1, H - y, I('sand', 1)); c.put(x, y, I('water', 6)); c.put(x, y + 1, I('mud', 1))
    for _ in range(2600):
        x, y = rng.randrange(W), rng.randint(270, H - 1); k = rng.random(); c.rect(x, y, 2 if k < .3 else 1, 1, I('pebble', 2) if k < .3 else I('sand', rng.randint(0, 3)))
    for _ in range(46):
        x, y = rng.randrange(W), rng.randint(274, H - 2); rx, ry = rng.randint(4, 11), rng.randint(2, 5); c.ellipse(x, y + 1, rx + 1, ry, I('sand', 0)); c.ellipse(x, y, rx, ry, I('pebble', 1)); c.ellipse(x - 1, y - 1, rx * .55, ry * .5, I('pebble', 2))
    g = R('wood_grey'); c.rect(600, 300, 128, 9, g[1]); c.hline(600, 728, 300, g[3]); c.hline(600, 728, 301, g[2]); c.hline(600, 728, 308, g[0]); c.ellipse(600, 304, 3, 5, g[3]); c.put(600, 304, g[1]); c.line(690, 300, 706, 286, g[1]); c.line(691, 300, 707, 286, g[2]); c.ellipse(650, 300, 8, 2, I('moss', 2))
    for x, y, f, rx in [(36, 306, 'fern', 30), (0, 350, 'shrub', 60), (798, 344, 'shrub', 66), (150, 352, 'fern', 26), (720, 352, 'fern', 30)]:
        blob(c, x, y, rx, 16, f, rng)
    return c

def marsh():
    rng = random.Random(33); c = Canvas(W, H, I('forest', 0)); band(c, 0, 66, 'haze_near', 2, 0)
    for x in range(-10, W, 34): blob(c, x + rng.randint(-8, 8), 58 + rng.randint(-6, 6), 30, 22, 'pine', rng, False)
    band(c, 76, 262, 'forest', 1, 0)           # peat water is not blue: tannin black-green with one tone of sky
    for y in range(76, 262):
        for x in range(0, W):
            if (x * 7 + y * 31) % 211 < 2: c.put(x, y, I('moss', 0))
    reflect(c, 76, 150, .4)
    for x in range(0, W): c.rect(x, 72 + int(3 * math.sin(x * .03)), 1, 6, I('mud', 0))
    def cattails(x0, x1, base, n, tall):
        for _ in range(n):
            x = rng.randint(x0, x1); h = rng.randint(*tall); y = base + rng.randint(-4, 6); lean = rng.choice((-1, 0, 0, 1)); fam = rng.choice(('reed', 'reed', 'fern'))
            c.line(x, y, x + lean, y - h, I(fam, rng.randint(0, 2)))
            if rng.random() < .5: c.rect(x + lean - 1, y - h - 5, 2, 6, I('wood', 1)); c.vline(x + lean - 1, y - h - 5, y - h, I('wood', 2)); c.line(x + lean, y - h - 6, x + lean, y - h - 9, I('reed', 2))
    cattails(0, 150, 110, 80, (24, 42)); cattails(620, 799, 112, 80, (22, 44)); cattails(280, 440, 96, 30, (14, 24))
    for (x, y, h, lean) in [(190, 170, 76, 10), (610, 150, 84, -12), (118, 214, 56, -8)]:   # drowned snags, standing dead
        g = R('wood_grey'); c.line(x, y, x + lean, y - h, g[1]); c.line(x + 1, y, x + 1 + lean, y - h, g[2]); c.line(x + 2, y, x + 2 + lean, y - h, g[1]); c.line(x + lean // 2, y - h // 2, x + lean // 2 + 14, y - h // 2 - 16, g[1]); c.line(x + lean // 2, y - h // 3, x + lean // 2 - 12, y - h // 3 - 14, g[2]); c.hline(x - 3, x + 5, y, I('moss', 0))
    for _ in range(26):
        x, y = rng.randrange(W), rng.randint(150, 256); c.ellipse(x, y, 5, 2, I('lily', 1)); c.ellipse(x - 1, y - 1, 3, 1, I('lily', 3)); c.put(x + 3, y, I('forest', 0))
        if rng.random() < .25: c.put(x, y - 2, I('flower_w', 2))
    for x in range(W):             # sodden bank: moss, peat, a tussock line
        y = 258 + int(7 * math.sin(x * .013) + 3 * math.sin(x * .07)); c.rect(x, y, 1, H - y, I('mud', 0)); c.rect(x, y, 1, 2, I('forest', 0)); c.rect(x, y + 2, 1, 2, I('moss', 0))
    for _ in range(1800):
        x, y = rng.randrange(W), rng.randint(266, H - 1); c.rect(x, y, rng.randint(1, 3), 1, I('moss', rng.randint(0, 2)) if rng.random() < .6 else I('mud', rng.randint(0, 2)))
    cattails(0, 210, 345, 70, (40, 80)); cattails(600, 799, 345, 70, (40, 86))
    for x in (250, 330, 490, 560): blob(c, x, 334, 20, 9, 'moss', rng)
    return c

def lake():
    rng = random.Random(44); c = Canvas(W, H, I('stone', 1)); band(c, 0, 92, 'ice', 3, 4)
    def peak(x, base, w, h, far):
        rock, sn = ('haze_far', 'snow') if far else ('stone', 'snow')
        for yy in range(h):
            half = w * (yy / h) ** .9
            for xx in range(int(x - half), int(x + half)):
                j = (xx * 13 + yy * 7) % 11; sh = (xx - x) > (yy * .1 + math.sin(yy * .4) * 3)
                if yy < h * .34 + 3 * math.sin(xx * .35):
                    fam, k = sn, (1 if sh else 3)
                else: fam, k = rock, (0 if sh else (2 if far else (2 if j < 7 else 3)))
                c.put(xx, base - h + yy, I(fam, k))
    for x, w, h in [(60, 120, 62), (240, 150, 74), (430, 130, 60), (610, 170, 82), (770, 110, 58)]: peak(x, 96, w, h, True)
    for x, w, h in [(150, 100, 42), (340, 92, 36), (520, 110, 48), (700, 96, 40)]: peak(x, 104, w, h, False)
    for x in range(-6, W, 9): # the pine line, dark, tight
        h = rng.randint(12, 26); y = 118 + rng.randint(-2, 2); c.poly([(x - 6, y), (x, y - h), (x + 6, y)], I('pine', rng.randint(0, 2))); c.line(x, y - h, x + 4, y - 3, I('pine', 3))
    band(c, 118, 264, 'water', 4, 2); 
    for x in range(W):
        for y in range(118, 264):
            if (x + y * 2) % 7 == 0 and y > 190: c.put(x, y, I('ice', 2))
    reflect(c, 118, 216, .85, jitter=True)
    for x in range(W): c.put(x, 118, I('ice', 4))
    for _ in range(90):
        x, y, l = rng.randrange(W), rng.randint(124, 258), rng.randint(3, 12); c.hline(x, x + l, y, I('ice', 4))
    for (x, y, rx, ry) in [(70, 250, 44, 12), (720, 246, 52, 14), (610, 262, 22, 8)]:
        c.ellipse(x, y, rx, ry, I('stone', 1)); c.ellipse(x - 2, y - 2, rx * .8, ry * .6, I('stone', 3)); c.hline(x - rx, x + rx, y + ry - 1, I('ice', 4))
    for x in range(W):
        y = 266 + int(4 * math.sin(x * .02) + 3 * math.sin(x * .09)); c.rect(x, y, 1, H - y, I('stone', 1)); c.put(x, y, I('ice', 4))
    for _ in range(420):
        x, y = rng.randrange(W), rng.randint(272, H - 1); rx = rng.randint(3, 12); ry = rng.randint(2, 5); c.ellipse(x, y, rx, ry, I('stone', rng.randint(1, 3))); c.ellipse(x - 1, y - 1, rx * .5, ry * .4, I('stone', rng.randint(3, 5))); 
    for x, y in [(36, 322), (770, 332), (660, 344), (140, 350)]:
        c.poly([(x - 18, y + 8), (x, y - 40), (x + 18, y + 8)], I('pine', 1)); c.poly([(x - 14, y - 6), (x, y - 52), (x + 12, y - 6)], I('pine', 2)); c.poly([(x - 9, y - 22), (x, y - 62), (x + 8, y - 22)], I('pine', 4)); c.rect(x - 1, y + 8, 3, 8, I('wood', 1))
    return c

def reservoir():
    rng = random.Random(55); c = Canvas(W, H, I('metal', 0)); ru = R('ruin'); band(c, 0, 150, 'ruin', 0, 1)
    def bricks(x0, y0, x1, y1, fam='ruin', base=1):
        for y in range(y0, y1):
            row = (y - y0) // 5; o = 8 if row % 2 else 0
            for x in range(x0, x1):
                edge = (y - y0) % 5 == 4 or (x + o) % 16 == 0; v = ((x + o) // 16 * 7 + row * 13) % 5
                c.put(x, y, I(fam, max(0, base - 1)) if edge else I(fam, base + (1 if v == 0 else 0)))
    bricks(0, 0, W, 150, 'ruin', 1)
    for cx in (130, 400, 670):     # the vault: three great arches with black beyond
        for y in range(36, 150):
            hw = 92 * math.sqrt(max(0, 1 - ((96 - min(y, 96)) / 60) ** 2)); c.hline(int(cx - hw), int(cx + hw), y, I('metal', 0))
        for a in np.arange(math.pi, 2 * math.pi, .012):
            for k in range(8): x, y = cx + math.cos(a) * (92 + k), 96 + math.sin(a) * (60 + k); c.put(int(x), int(y), I('ruin', 2 + (k % 8 == 7) + (int(a * 24) % 3 == 0)))
        band(c, 96, 150, 'metal', 0, 0, cx - 88, cx + 88)
    for x in range(W):                # distant inner arches through the openings, one tone up
        if x % 66 < 3: c.vline(x, 100, 148, I('metal', 1))
    # shaft of grey light from a grate, falling on the water
    for y in range(0, 262):
        cx = 400 + y * .04; hw = 8 + y * .1
        for x in range(int(cx - hw), int(cx + hw)):
            if ((x // 3) * 5 + y * 7) % 16 / 16 < .34 - y * .0006: c.put(x, y, I('moonlight', 0))
    c.rect(384, 0, 34, 7, I('metal', 0)); [c.rect(386 + k * 5, 1, 2, 6, I('metal_rust', 1)) for k in range(7)]
    band(c, 150, 264, 'water', 0, 1)
    for y in range(150, 264):
        for x in range(W):
            if (x * 3 + y * 11) % 61 < 2: c.put(x, y, I('water', 2))
    reflect(c, 150, 240, .6)
    for x in (260, 540):         # columns stand in the water
        bricks(x - 12, 40, x + 12, 196, 'ruin', 2); c.vline(x - 12, 40, 196, I('ruin', 4)); c.vline(x + 11, 40, 196, I('ruin', 0)); c.rect(x - 16, 34, 32, 8, I('ruin', 3)); c.hline(x - 16, x + 16, 34, I('ruin', 5))
        c.hline(x - 13, x + 13, 197, I('moonlight', 0)); c.ellipse(x, 199, 16, 2, I('water', 0))
        for k in range(14): c.put(x - 12 + k * 2, 162 + (k % 3), I('metal', 0))   # the old water line
    # rust pipes along the wall, one weeping
    for (y, x0, x1) in [(30, 0, 200), (24, 600, 800)]:
        c.rect(x0, y, x1 - x0, 7, I('metal_rust', 1)); c.hline(x0, x1, y, I('metal_rust', 2)); c.hline(x0, x1, y + 6, I('metal_rust', 0)); 
        for x in range(x0 + 8, x1, 40): c.rect(x, y - 1, 3, 9, I('metal', 2))
    c.vline(90, 37, 150, I('metal_rust', 0)); c.vline(712, 31, 150, I('metal_rust', 1))
    # fungus is the only lamp down here
    for (x, y, n) in [(40, 138, 7), (222, 132, 5), (300, 120, 4), (496, 138, 6), (606, 130, 5), (768, 140, 7), (528, 60, 3), (274, 66, 3)]:
        for k in range(n):
            xx = x + rng.randint(-10, 10); yy = y + rng.randint(-5, 5); c.vline(xx, yy, yy + 3, I('shroom_stem', 0)); c.rect(xx - 2, yy - 1, 5, 2, I('glowshroom', 1)); c.hline(xx - 1, xx + 1, yy - 2, I('glowshroom', 2))
    # concrete apron underfoot, cracked and stained
    for x in range(W): c.rect(x, 264, 1, H - 264, I('rubble', 1))
    c.hline(0, W, 264, I('ruin', 4)); c.hline(0, W, 265, I('ruin', 3))
    for x in range(0, W, 66): c.vline(x + 18, 266, H, I('rubble', 0))
    for _ in range(500): x, y = rng.randrange(W), rng.randint(268, H - 1); c.rect(x, y, rng.randint(1, 4), 1, I('rubble', rng.randint(0, 2)))
    for x, l in [(120, 90), (580, 70)]: c.line(x, 266, x + 12, 310, I('rubble', 0)); c.line(x + 12, 310, x + 4, H, I('rubble', 0))
    c.rect(0, 272, 18, 88, I('metal_rust', 0)); c.rect(782, 280, 18, 80, I('metal_rust', 1))
    return c
def tide():
    """The Silent Tide: kneeling on clear ice, looking down into the drowned town. Roofs, a street, lit windows, a bell tower; the ice over it all."""
    rng = random.Random(88); c = Canvas(W, H, I('water', 0)); band(c, 0, 290, 'water', 0, 1)
    def house(x, y, w, h, roof='ruin'):
        c.rect(x, y, w, h, I('ruin', 1)); c.rect(x, y, w, 2, I('ruin', 2)); c.poly([(x - 3, y), (x + w // 2, y - h // 2), (x + w + 3, y)], I(roof, 1)); c.line(x - 3, y, x + w // 2, y - h // 2, I(roof, 2))
        for k in range(max(1, w // 10)):
            wx = x + 4 + k * 10
            if wx + 4 < x + w: c.rect(wx, y + 4, 4, 5, I('lantern_glass', rng.choice((0, 1, 2)) if rng.random() < .7 else 0) if rng.random() < .75 else I('metal', 0))
    c.rect(0, 160, W, 28, I('ruin', 0)); [c.hline(0, W, 160 + k * 7, I('rubble', 0)) for k in range(4)]                       # the drowned street
    for (x, y, w, h) in [(30, 120, 54, 34), (110, 96, 64, 44), (200, 126, 46, 30), (520, 104, 60, 40), (610, 128, 50, 30), (690, 98, 70, 46), (60, 230, 60, 36), (170, 250, 50, 30), (560, 236, 64, 40), (660, 250, 54, 34)]: house(x, y, w, h, 'metal_rust' if x % 3 else 'ruin')
    c.rect(374, 40, 52, 110, I('ruin', 1)); c.poly([(368, 40), (400, 4), (432, 40)], I('metal_rust', 1)); c.rect(390, 54, 20, 22, I('lantern_glass', 1)); c.ellipse(400, 66, 7, 7, I('metal_rust', 2)); c.put(400, 70, I('metal', 0))   # the bell tower, its window lit
    for _ in range(60): x, y = rng.randrange(W), rng.randint(20, 280); c.ellipse(x, y, rng.randint(2, 6), 1, I('lily', 0) if rng.random() < .5 else I('moss', 0))   # weed in the streets
    for y in range(0, 300):                                    # the ice: sheen and long cracks over everything
        for x in range(W):
            if ((x // 9) * 5 + (y // 2) * 11) % 47 < 2 and (x + y) % 3: c.put(x, y, I('ice', 2))
    for _ in range(9):
        x, y = rng.randrange(W), rng.randint(10, 280); a = rng.random() * 3.14
        for t in range(rng.randint(30, 90)): x += math.cos(a); y += math.sin(a) * .5; a += rng.uniform(-.2, .2); c.put(int(x), int(y), I('ice', 4))
    for x in range(W): y = 290 + int(4 * math.sin(x * .02)); c.rect(x, y, 1, H - y, I('snow', 3)); c.put(x, y, I('snow', 4))
    for _ in range(700): x, y = rng.randrange(W), rng.randint(294, H - 1); c.put(x, y, I('snow', rng.choice((2, 3, 4))))
    c.ellipse(400, 222, 26, 12, I('ice', 3)); c.ellipse(400, 222, 21, 9, I('water', 0)); c.ellipse(399, 220, 12, 4, I('water', 1))     # the ice hole
    for k in range(10): a = k / 10 * 6.28; c.rect(int(400 + math.cos(a) * 34) - 2, int(222 + math.sin(a) * 15) - 3, 4, 5, I('ice', 3)); c.put(int(400 + math.cos(a) * 34), int(222 + math.sin(a) * 15) - 1, I('lantern_glass', 2))
    return c
ALL = dict(stream=stream, marsh=marsh, lake=lake, reservoir=reservoir, tide=tide)

def trail_sign():
    """Finger-post at the head of the trail: one solid post, two warm boards."""
    c = Canvas(24, 30); w = R('wood'); c.rect(10, 2, 4, 27, w[2]); c.vline(10, 2, 28, w[4]); c.vline(13, 2, 28, w[1]); c.hline(8, 15, 28, w[0]); c.rect(10, 1, 4, 2, w[5])
    for (x, y, l, d) in ((1, 5, 21, 1), (3, 13, 19, -1)):
        c.rect(x, y, l, 6, w[3]); c.hline(x, x + l - 1, y, w[5]); c.hline(x, x + l - 1, y + 5, w[1]); c.hline(x + 3, x + l - 4, y + 2, w[1]); c.hline(x + 5, x + l - 6, y + 3, w[2])
        tip = x + l if d > 0 else x - 1; c.vline(tip, y + 1, y + 4, w[2])
    c.put(9, 27, R('moss')[2]); c.put(14, 27, R('moss')[1]); return (c, 12, 29)
def worm_bed():
    c = Canvas(18, 10); e = R('dirt'); c.ellipse(9, 6, 8, 3.4, e[1]); c.ellipse(8, 5, 6, 2.4, e[2]); c.put(5, 4, e[3]); c.put(11, 6, e[3]); pk = R('flower_p'); c.line(6, 6, 9, 5, pk[1]); c.put(9, 4, pk[2]); c.line(12, 4, 14, 6, pk[1]); return c
def worm_empty():
    c = Canvas(18, 10); e = R('dirt'); c.ellipse(9, 6, 8, 3.4, e[1]); c.ellipse(8, 5, 6, 2.4, e[2]); return c
def reed_insects():
    c = Canvas(14, 20); r = R('reed'); [c.line(x, 19, x + l, 6 + k, r[1 + k % 3]) for k, (x, l) in enumerate([(3, -1), (6, 1), (9, 2), (11, 1)])]; ey = R('firefly')[0]; c.put(3, 8, R('metal')[0]); c.put(4, 8, R('flower_b')[2]); c.put(9, 5, R('metal')[0]); c.put(10, 5, R('flower_b')[2]); c.put(10, 4, R('flower_w')[2]); c.put(6, 11, ey); return c
def reed_empty():
    c = Canvas(14, 20); r = R('reed'); [c.line(x, 19, x + l, 6 + k, r[1 + k % 3]) for k, (x, l) in enumerate([(3, -1), (6, 1), (9, 2), (11, 1)])]; return c
def nodes(): return dict(worm_bed=(worm_bed(), worm_empty(), 9, 9), reed_insects=(reed_insects(), reed_empty(), 7, 19))
