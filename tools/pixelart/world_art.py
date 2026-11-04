"""The rest of the world's set pieces, in the same hand as the campsite (camp_art.py) and the trees (tree_art.py):
light from the upper left, each form lit / mid / shaded, selective outlines in the material's darkest tone, details
that say what the material is (wood grain and nail heads, mortar and moss, wet stems going dark at the waterline).

  water and shore   cattails, lily pads (with and without flowers), arrowhead, sedge, marsh grass
  ground            grass tufts, fallen hollow log with shelf fungus, fallen branches, an upturned root plate
  wood structures   the fishing dock, the footbridge, split-rail fence, way-sign
  ruin              the arched wall with its dark doorway and steps down, a broken pillar, a low wall, rubble, a fallen beam,
                    a hanging lantern
  highland          stone ledges (layered rock shelves), scree, heather
  mysterious        glow-caps that light the dark
"""
from __future__ import annotations
import math, random
import numpy as np
from .canvas import Canvas
from .palette import PAL
from .noise import value_noise
from .camp_art import lit_blob, sel_outline, faceted, _sprite, _curve, _log

R = PAL.ramp


def _edge(c, m=None):
    m = (c.a != 0) if m is None else m
    p = np.pad(m, 1)
    return m & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])


def _outline_fams(c, pairs):
    """Outline each material in its own darkest tone."""
    e = _edge(c)
    for ramp in pairs:
        sel = e & np.isin(c.a, list(ramp[1:]))
        c.a[sel] = ramp[0]


# ---------------------------------------------------------------------------------------------------------------- water plants
def cattails(name, seed, n=9, h=30):
    """A stand of cattails: long blades arching from the water, darker and wetter at the foot, a few brown velvet
    heads on stiff stalks, one gone to seed."""
    W, H = 22, h + 6
    c = Canvas(W, H); rd = R('reed'); wd = R('wood'); rng = random.Random(seed)
    bx, by = W // 2, H - 2
    blades = sorted([(rng.uniform(-0.55, 0.55), rng.uniform(0.55, 1.0) * h, rng.uniform(-0.04, 0.04)) for _ in range(n)], key=lambda q: abs(q[0]), reverse=True)
    for (ang, L, bend) in blades:
        x0 = bx + int(ang * 5)
        def col(t, x, y, a=ang):
            if 0 <= x < W and 0 <= y < H: c.put(x, y, rd[0] if t < 0.12 else rd[1] if t < 0.4 else (rd[2] if a < 0.1 else rd[1]) if t < 0.85 else rd[3])
        _curve(c, x0, by, ang * 0.35, L, bend + ang * 0.03, col)
    for k in range(3):                                            # heads
        x = bx + rng.randint(-5, 5); top = by - int(h * rng.uniform(0.8, 1.0))
        c.vline(x, top, by - 3, rd[1]); c.put(x, top - 1, rd[2])
        if k < 2:
            for y in range(top + 2, top + 7): c.put(x, y, wd[2]); c.put(x + 1, y, wd[1])
            c.put(x, top + 2, wd[3])
        else:
            for y in range(top + 2, top + 6): c.put(x, y, R('flower_w')[0]); c.put(x + 1, y, wd[3])
    return _sprite(name, c, bx, by + 1, shadow=None, tags=('plant', 'ysort', 'water'))


def lily(name, seed, r=4.0, flower=None):
    """A lily pad lying on the water: a flattened disc with its notch, veins radiating, a lit near rim and a wet dark
    far rim; optionally a water-lily flower sitting on it."""
    W, H = int(r * 2 + 6), int(r * 1.2 + 7)
    c = Canvas(W, H); ly = R('lily'); rng = random.Random(seed)
    cx, cy = W / 2, H / 2 + 1
    na = rng.uniform(0, 2 * math.pi)
    for y in range(H):
        for x in range(W):
            u = (x + .5 - cx) / r; v = (y + .5 - cy) / (r * 0.55)
            if u * u + v * v > 1: continue
            a = math.atan2(v, u); da = abs((a - na + math.pi) % (2 * math.pi) - math.pi)
            if da < 0.28 and u * u + v * v > 0.08: continue          # the notch
            t = 2 if v > 0.1 else 3
            if v > 0.6: t = 1
            if (round(math.degrees(a)) // 40) % 2 == 0 and 0.2 < u * u + v * v < 0.8 and t > 1: t -= 1   # veins
            if u < -0.3 and v < -0.2: t = 3
            c.put(x, y, ly[t])
    sel_outline(c, c.a != 0, ly)
    if flower:
        fr = R(flower)
        fx, fy = int(cx + rng.uniform(-1, 1)), int(cy - 1)
        for (dx, dy, k) in ((0, -2, 2), (-1, -1, 2), (1, -1, 1), (-2, 0, 1), (2, 0, 0), (0, -1, 2), (-1, 0, 2), (1, 0, 1), (0, 0, 2)):
            c.put(fx + dx, fy + dy, fr[k] if k < len(fr) else fr[-1])
        c.put(fx, fy - 1, PAL.i('flower_y', 2))
    return _sprite(name, c, int(cx), int(cy + r * 0.55), shadow=None, tags=('water',))


ARROW = ["..L..", ".LLL.", "LLMLL", "LM.ML", "D...D"]


def arrowhead(name, seed):
    """Arrowhead: arrow-shaped leaves held up on stems out of the shallows, and one white flower spike."""
    W, H = 18, 20
    c = Canvas(W, H); ly = R('lily'); rng = random.Random(seed)
    bx, by = W // 2, H - 2
    tones = {'L': ly[3], 'M': ly[2], 'D': ly[1]}
    for k, (dx, h) in enumerate(((-5, 10), (3, 13), (6, 8), (-1, 15))):
        x = bx + dx; top = by - h
        c.vline(x, top + 4, by, ly[1] if k % 2 else ly[2])
        for yy, row in enumerate(ARROW):
            for xx, ch in enumerate(row):
                if ch != '.': c.put(x - 2 + xx, top + yy, tones[ch])
    x = bx + 1; c.vline(x, 1, by - 2, ly[1])
    for y in (1, 3, 5): c.put(x - 1, y, R('flower_w')[2]); c.put(x + 1, y, R('flower_w')[1])
    _outline_fams(c, [ly])
    return _sprite(name, c, bx, by + 1, shadow=None, tags=('plant', 'ysort', 'water'))


def sedge(name, seed, h=12, fam='reed'):
    """Marsh sedge: a dense tussock of fine blades, the outer ones flopping over, khaki-green with dry tips."""
    W, H = 20, h + 4
    c = Canvas(W, H); rd = R(fam); rng = random.Random(seed)
    bx, by = W // 2, H - 2
    for k in range(16):
        ang = rng.uniform(-1.1, 1.1); L = h * rng.uniform(0.55, 1.0)
        def col(t, x, y, a=ang):
            if 0 <= x < W and 0 <= y < H: c.put(x, y, rd[0] if t < 0.2 else rd[1] if t < 0.55 else rd[2] if abs(a) < 0.7 else rd[1] if t < 0.9 else rd[3])
        _curve(c, bx + int(ang * 3), by, ang * 0.5, L, ang * 0.06, col)
    c.hline(bx - 3, bx + 3, by, rd[0])
    return _sprite(name, c, bx, by + 1, shadow=(6, 1.5, 1, 0), soft_shadow=True, tags=('plant', 'ysort'), contact=(4, 0.8))


def tuft(name, seed, h=7):
    """A small grass tuft for the meadow: six or seven blades, a dark heart, lit tips."""
    W, H = 12, h + 3
    c = Canvas(W, H); g = R('grass'); rng = random.Random(seed)
    bx, by = W // 2, H - 2
    for k in range(7):
        ang = rng.uniform(-0.8, 0.8); L = h * rng.uniform(0.5, 1.0)
        def col(t, x, y):
            if 0 <= x < W and 0 <= y < H: c.put(x, y, g[2] if t < 0.3 else g[3] if t < 0.75 else g[4])
        _curve(c, bx + int(ang * 2), by, ang * 0.6, L, ang * 0.05, col)
    c.hline(bx - 1, bx + 1, by, g[1])
    return _sprite(name, c, bx, by + 1, shadow=None, tags=('plant', 'ysort', 'grass'))


def glowcaps(name, seed):
    """Glow-caps: a cluster of pale mushrooms that hold a cold light, on a cushion of dark moss."""
    W, H = 14, 11
    c = Canvas(W, H); gl = R('glowshroom'); mo = R('moss'); ss = R('shroom_stem'); rng = random.Random(seed)
    for x in range(1, 13): c.put(x, 10, mo[0] if x % 2 else mo[1])
    for (x, h, r) in ((4, 4, 2.2), (8, 6, 2.8), (11, 3, 1.6)):
        for y in range(10 - h, 10): c.put(x, y, ss[1])
        cy = 10 - h - 1
        c.ellipse(x + 0.5, cy, r, r * 0.6, gl[1]); c.ellipse(x, cy - 0.4, r * 0.6, r * 0.35, gl[2]); c.hline(int(x + 0.5 - r + 1), int(x + 0.5 + r - 1), int(cy + r * 0.5), gl[0])
        c.put(int(x), int(cy - 1), gl[2])
    return _sprite(name, c, 7, 11, shadow=None, tags=('plant', 'ysort', 'light'))


# ---------------------------------------------------------------------------------------------------------------- fallen wood
def hollow_log(name, seed):
    """A fallen trunk: a big log lying across the view with the dark mouth of its hollow end, bark plates, shelf
    fungus stepping along its side, moss on the top, and the torn stub of a branch."""
    W, H = 48, 24
    c = Canvas(W, H); wd = R('wood'); mo = R('moss'); sh = R('shroom')
    _log(c, 4, 13, 38, 7, seed=seed, moss=True)
    ex, ey = 42, 13                                                # hollow end: dark inside the rings
    c.ellipse(ex, ey, 3.6, 7.2, wd[3]); c.ellipse(ex, ey, 2.4, 5.4, wd[4]); c.ellipse(ex + 0.3, ey + 0.4, 1.6, 4.2, R('tent_interior')[0])
    c.ellipse(ex + 0.6, ey + 1.6, 0.9, 2.2, PAL.i('ember', 0))
    for (x, y) in ((14, 16), (17, 15), (20, 17)):                 # shelf fungus
        c.hline(x - 1, x + 2, y, sh[3]); c.hline(x - 1, x + 2, y + 1, sh[1]); c.put(x + 2, y + 1, sh[0])
    for x in range(6, 26):                                         # thicker moss blanket on the top
        if value_noise(x, 2, 3.0, seed) > 0.4: c.put(x, 6, mo[2]); c.put(x, 7, mo[1])
    _outline_fams(c, [wd])
    return _sprite(name, c, 22, 21, shadow=(21, 3, 2, 0), soft_shadow=True, tags=('prop', 'ysort', 'solid'), contact=(19, 1.8), ground_blend=True)


def branch(name, seed):
    """A fallen branch: a crooked limb with side twigs and a few dead leaves, lying in the grass."""
    W, H = 28, 10
    c = Canvas(W, H); wd = R('wood'); lf = R('leaf_litter'); rng = random.Random(seed)
    y = 6
    for x in range(2, 25):
        yy = y + (1 if 8 < x < 15 else 0)
        c.put(x, yy, wd[3]); c.put(x, yy + 1, wd[1]) if x < 18 else None
    for (x, dx) in ((7, -1), (12, 1), (18, -1), (21, 1)):
        for k in range(1, 4): c.put(x + k * dx, y - k, wd[2])
        c.put(x + 4 * dx, y - 4, lf[2]); c.put(x + 4 * dx + 1, y - 4, lf[1])
    _outline_fams(c, [wd])
    return _sprite(name, c, 13, 9, shadow=None, tags=('prop', 'ysort'))


def root_plate(name, seed):
    """The upturned root plate of the fallen tree: a disc of earth held in roots, dark beneath."""
    W, H = 30, 26
    c = Canvas(W, H); wd = R('wood'); ea = R('earth'); rng = random.Random(seed)
    lit_blob(c, 15, 12, 11, 10, ea, seed=seed, rough=0.5, lo=1, hi=3, outline=False)
    for k in range(9):
        a = rng.uniform(0, 2 * math.pi); L = rng.uniform(6, 13)
        _curve(c, 15, 12, a, L, rng.uniform(-0.1, 0.1), lambda t, x, y: c.put(x, y, wd[2] if t < 0.6 else wd[3]))
    for (x, y) in ((12, 8), (17, 10), (14, 15)): c.put(x, y, PAL.i('pebble', 2))
    sel_outline(c, c.a != 0, ea)
    return _sprite(name, c, 15, 23, shadow=(10, 2.5, 1, 0), soft_shadow=True, tags=('prop', 'ysort'), contact=(8, 1.4))


# ---------------------------------------------------------------------------------------------------------------- wood structures
def _plank_tones(wd, k, x):
    return wd[4] if k % 3 == 0 else wd[3] if k % 3 == 1 else wd[4]


def dock():
    """The fishing dock: a deck of weathered planks running out over the water, nail heads at the joists, darker
    gaps between boards, posts with their wet dark feet in the water, a coil of rope and a mooring cleat."""
    W, H = 70, 30
    c = Canvas(W, H); wd = R('wood_grey'); ww = R('wood'); mt = R('metal'); rp = R('rope'); wa = R('water')
    x0, x1, top, bot = 2, 66, 6, 21
    for x in range(x0, x1 + 1):                                     # boards run across the deck, one tone each
        k = (x - x0) // 4; gap = (x - x0) % 4 == 3
        for y in range(top, bot + 1):
            t = 1 if gap else (4 if k % 3 == 0 else 3 if k % 3 == 1 else 4)
            if not gap and (y == top): t = min(4, t + 0)
            if not gap and value_noise(x, y * 3, 2.0, k) > 0.8: t -= 1               # grain
            c.put(x, y, wd[t])
        if not gap: c.put(x, top, wd[4])
    c.hline(x0, x1, top - 1, wd[2])                                  # far edge
    c.hline(x0, x1, bot + 1, wd[1]); c.hline(x0, x1, bot + 2, wd[0])   # near fascia in shade
    for x in range(x0 + 1, x1, 8):                                   # nail heads on the joists
        for y in (top + 2, bot - 2): c.put(x, y, mt[2])
    for x in (x0 + 2, x0 + 22, x0 + 42, x1 - 2):                     # posts, wet at the foot
        for y in range(bot + 1, H - 1): c.put(x, y, wd[2]); c.put(x + 1, y, wd[1])
        c.put(x, H - 2, wa[1]); c.put(x + 1, H - 2, wa[0]); c.hline(x - 1, x + 2, H - 1, wa[3])
    for x in (x0 + 2, x1 - 2):                                       # the two end posts stand proud of the deck
        for y in range(top - 5, top): c.put(x, y, wd[3]); c.put(x + 1, y, wd[2])
        c.put(x, top - 6, wd[4])
    c.ellipse(x1 - 10, top + 5, 3, 2, rp[1]); c.ellipse(x1 - 10, top + 5, 1.6, 1, rp[0]); c.put(x1 - 12, top + 4, rp[2])   # rope coil
    c.hline(x0 + 30, x0 + 33, bot - 1, mt[2]); c.put(x0 + 31, bot - 2, mt[3])          # cleat
    _outline_fams(c, [wd])
    return _sprite('dock', c, 2, 24, shadow=(25, 3, 3, 3), tags=('structure', 'ysort'))


def bridge():
    """The footbridge over the river: a low arch of planks between rails on stout posts, the deck lit, the rails
    with a lit top and a shaded face, cross-braces under the rails, the posts' feet in the water."""
    W, H = 118, 32
    c = Canvas(W, H); wd = R('wood'); wa = R('water')
    cx = 59
    def arch(x): return int(round(4 * (1 - ((x - cx) / 56) ** 2)))
    for x in range(2, 116):                                          # deck: planks across, rising to the middle
        a = arch(x); k = x // 3
        for y in range(16 - a, 26 - a):
            t = 1 if x % 3 == 2 else (4 if k % 2 else 3)
            if y == 16 - a and t > 1: t = 5 if k % 2 else 4
            c.put(x, y, wd[min(5, t)])
        c.put(x, 26 - a, wd[1]); c.put(x, 27 - a, wd[0])
    for rail_y, k in ((7, 0), (13, 1)):                              # far rail, near rail
        for x in range(2, 116):
            a = arch(x); y = rail_y - a + (6 if k else 0)
            c.put(x, y, wd[4]); c.put(x, y + 1, wd[2]); c.put(x, y + 2, wd[1])
    for x in list(range(2, 117, 19)) + [115]:                        # posts with braces
        a = arch(x)
        for y in range(5 - a, 30 - a if x in (2, 115) else 28 - a):
            c.put(x, y, wd[3]); c.put(x + 1, y, wd[2])
        c.put(x, 4 - a, wd[4]); c.put(x + 1, 4 - a, wd[3])
        if x < 110:
            c.line(x + 2, 8 - a, x + 9, 13 - a, wd[2])
    for x in (3, 114): c.hline(x - 2, x + 3, 30, wa[3])
    _outline_fams(c, [wd])
    return _sprite('bridge', c, 59, 29, shadow=None, tags=('structure', 'ysort'))


def fence(name, seed, n=3):
    """A split-rail fence: n bays of two rails between leaning posts, grey weathered wood, a rail end cracked."""
    W, H = n * 16 + 4, 20
    c = Canvas(W, H); wd = R('wood_grey'); rng = random.Random(seed)
    for k in range(n + 1):
        x = 2 + k * 16 + rng.randint(-1, 1)
        for y in range(3, 18): c.put(x, y, wd[3]); c.put(x + 1, y, wd[2])
        c.put(x, 2, wd[4]); c.put(x + 1, 2, wd[3])
    for ry in (6, 11):
        for x in range(2, W - 2):
            y = ry + (1 if (x // 16 + seed) % 2 and x % 16 > 8 else 0)
            c.put(x, y, wd[4]); c.put(x, y + 1, wd[2])
    _outline_fams(c, [wd])
    return _sprite(name, c, W // 2, 18, shadow=(W // 2 - 2, 2, 1, 0), soft_shadow=True, tags=('structure', 'ysort', 'solid'), contact=(W // 2 - 3, 1.0))


def signpost(name='signpost'):
    """A way-sign: a post with two arrow boards pointing different ways, letters suggested by darker strokes."""
    W, H = 22, 30
    c = Canvas(W, H); wd = R('wood')
    for y in range(4, 28): c.put(10, y, wd[3]); c.put(11, y, wd[2])
    for (y, d) in ((6, 1), (13, -1)):
        x0, x1 = (4, 19) if d > 0 else (2, 17)
        c.rect(x0, y, x1 - x0, 5, wd[4]); c.hline(x0, x1 - 1, y, wd[5]); c.hline(x0, x1 - 1, y + 4, wd[2])
        tip = x1 if d > 0 else x0 - 1
        for k in range(3): c.vline(tip + d * k, y + k, y + 4 - k, wd[4] if k < 2 else wd[3])
        for x in range(x0 + 2, x1 - 2, 3): c.put(x, y + 2, wd[1]); c.put(x + 1, y + 2, wd[1])
    for (x, k) in ((8, 2), (13, 1)): c.put(x, 28, wd[k])
    _outline_fams(c, [wd])
    return _sprite(name, c, 11, 29, shadow=(5, 1.5, 3, 0), soft_shadow=True, tags=('structure', 'ysort', 'solid'), contact=(3, 1.0))


# ---------------------------------------------------------------------------------------------------------------- the ruin
def masonry(c, x0, y0, x1, y1, seed, ramp=None, top_profile=None, moss=0.0):
    """Fill a rectangle with coursed stone: blocks of varied length in rows that step their joints, each block lit
    on its top edge and shaded along its foot, mortar lines darker; an irregular broken top; moss on top edges."""
    rm = ramp or R('ruin'); mo = R('moss'); rng = random.Random(seed)
    y = y1
    row = 0
    while y > y0:
        hgt = rng.choice((4, 5, 5, 6)); yt = max(y0, y - hgt + 1); x = x0 - rng.randint(0, 6)
        while x <= x1:
            L = rng.randint(6, 12)
            tone = rng.choice((2, 3, 3, 4))
            for xx in range(max(x0, x), min(x1, x + L - 1) + 1):
                top = top_profile(xx) if top_profile else y0
                for yy in range(yt, y + 1):
                    if yy < top: continue
                    t = tone
                    if yy == yt or yy == top: t = min(5, tone + 1)
                    elif yy == y: t = max(1, tone - 1)
                    if xx == x + L - 1 or xx == x1: t = max(1, tone - 1)
                    c.put(xx, yy, rm[t])
            for yy in range(yt, y + 1):                         # vertical mortar joint
                if x0 <= x + L - 1 <= x1 and (not top_profile or yy >= top_profile(x + L - 1)): c.put(x + L - 1, yy, rm[0] if yy > yt else rm[1])
            if value_noise(x, y, 3.0, seed) > 0.8:               # a cracked, darker block
                c.put(min(x1, x + L // 2), yt + 1, rm[1]); c.put(min(x1, x + L // 2 + 1), yt + 2, rm[1])
            x += L
        if yt - 1 > y0:                                                  # bed joint, only inside the wall
            for xx in range(x0, x1 + 1):
                if not top_profile or yt - 1 >= top_profile(xx): c.put(xx, yt - 1, rm[1])
        y = yt - 2; row += 1
    if moss:
        for xx in range(x0, x1 + 1):
            top = top_profile(xx) if top_profile else y0
            if value_noise(xx, 0, 4.0, seed + 3) < moss:
                for k in range(1 + (value_noise(xx, 1, 2.0, seed) > 0.6)): c.put(xx, top + k, mo[2] if k == 0 else mo[1])


def ruin_back():
    """The arched wall of the old station: coursed stone with a broken top, an arch of wedge-shaped voussoirs around
    a doorway into the dark, worn steps going down inside, ivy falling from the top, moss along the ledges.
    The doorway is the dark door of the storylines: it stays open (collision leaves it walkable)."""
    W, H = 128, 64
    c = Canvas(W, H); rm = R('ruin'); mo = R('moss'); fe = R('fern'); ti = R('tent_interior')
    ox = 63
    def prof(x):
        return int(14 + 10 * value_noise(x, 0, 14.0, 9) + (8 if x < 30 or x > 104 else 0) - (6 if abs(x - (ox - 3)) < 18 else 0))
    masonry(c, ox - 47, 6, ox + 47, 60, seed=5, top_profile=prof, moss=0.55)
    # the arch and the doorway
    ax, aw, ab = ox - 3, 10, 60
    atop = ab - 30
    for y in range(atop - 4, ab + 1):
        for x in range(ax - aw - 4, ax + aw + 5):
            dy = max(0, (atop + aw) - y); d = math.hypot(x - ax, dy)
            if y >= atop + aw and abs(x - ax) <= aw or (y < atop + aw and d <= aw): c.put(x, y, ti[0])           # the dark
            elif (y >= atop + aw and aw < abs(x - ax) <= aw + 4) or (y < atop + aw and aw < d <= aw + 4):
                ang = math.atan2(dy, x - ax); k = int(ang / (math.pi / 9))
                t = 4 if (k % 2) else 3
                if (y < atop + aw and d > aw + 3) or (y >= atop + aw and abs(x - ax) > aw + 3): t = 1
                if (y < atop + aw and d <= aw + 1) or (y >= atop + aw and abs(x - ax) <= aw + 1): t = 2
                c.put(x, y, rm[t])
    c.rect(ax - 2, atop - 4, 5, 4, rm[5]); c.hline(ax - 2, ax + 2, atop, rm[2])                      # keystone
    for k, y in enumerate(range(ab - 2, ab - 14, -3)):                                                 # steps going down into the dark
        w = aw - 1 - k
        c.hline(ax - w, ax + w, y, ti[2] if k == 0 else ti[1]); c.hline(ax - w, ax + w, y + 1, ti[0])
    c.put(ax - 5, ab - 13, R('glowshroom')[2]); c.put(ax + 4, ab - 11, R('glowshroom')[1])          # a cold light far inside
    # ivy falling from the wall top
    rng = random.Random(3)
    for x in list(range(ox - 44, ox - 20, 3)) + list(range(ox + 18, ox + 44, 4)):
        top = prof(x); L = rng.randint(6, 18)
        for y in range(top, min(H - 3, top + L)):
            if c.get(x, y) and c.get(x, y) != ti[0]: c.put(x, y, fe[2] if (y + x) % 3 else fe[3])
            if (y - top) % 4 == 2: c.put(x + 1, y, fe[1])
    m = c.a != 0
    e = _edge(c, m)
    c.a[e & np.isin(c.a, list(rm[1:]))] = rm[0]
    return _sprite('ruin_back', c, 63, 62, shadow=(46, 4, 4, 3), tags=('structure', 'ysort'))


def ruin_side():
    """A broken pillar at the corner of the old station, two courses of wall still leaning on it to the left."""
    W, H = 60, 61
    c = Canvas(W, H); rm = R('ruin')
    masonry(c, 37, 10, 48, 59, seed=11, top_profile=lambda x: 10 + (x % 5 == 0) * 2 + (4 if x > 45 else 0), moss=0.5)
    masonry(c, 4, 40, 36, 59, seed=13, top_profile=lambda x: int(40 + 8 * value_noise(x, 0, 9.0, 4)), moss=0.4)
    e = _edge(c); c.a[e & np.isin(c.a, list(rm[1:]))] = rm[0]
    return _sprite('ruin_side', c, 42, 59, shadow=(21, 3, 3, 1), tags=('structure', 'ysort'))


def ruin_wall():
    """A low run of broken wall, waist-high, moss on its top."""
    W, H = 92, 38
    c = Canvas(W, H); rm = R('ruin')
    masonry(c, 2, 8, 89, 35, seed=21, top_profile=lambda x: int(8 + 14 * value_noise(x, 0, 16.0, 6) + (x > 70) * 4), moss=0.6)
    e = _edge(c); c.a[e & np.isin(c.a, list(rm[1:]))] = rm[0]
    return _sprite('ruin_wall', c, 46, 36, shadow=(40, 3, 3, 1), tags=('structure', 'ysort'))


def rubble(name, seed):
    """Fallen blocks heaped where a wall came down: dressed stones with their square edges, one broken, moss between."""
    W, H = 32, 19
    c = Canvas(W, H); rm = R('ruin'); mo = R('moss'); rng = random.Random(seed)
    for (x, y, w, h) in sorted([(2, 10, 10, 7), (11, 8, 11, 9), (21, 11, 9, 6), (7, 3, 10, 7), (17, 2, 8, 6)], key=lambda q: q[1] + q[3]):
        x += rng.randint(-1, 1)
        c.rect(x, y, w, h, rm[3]); c.hline(x, x + w - 1, y, rm[4]); c.vline(x + w - 1, y + 1, y + h - 1, rm[1]); c.hline(x, x + w - 1, y + h - 1, rm[1])
        c.put(x + w // 2, y + 2, rm[2])
    for x in range(2, 30, 3):
        if rng.random() < 0.5: c.put(x, 16, mo[1]); c.put(x + 1, 15, mo[2])
    e = _edge(c); c.a[e & np.isin(c.a, list(rm[1:]))] = rm[0]
    return _sprite(name, c, 16, 17, shadow=(11, 2, 1, 1), tags=('prop', 'ysort'), contact=(10, 1.2), ground_blend=True)


def beam():
    """A fallen roof beam, square-sawn, silvered, its end split, half sunk in grass."""
    W, H = 40, 12
    c = Canvas(W, H); wd = R('wood_grey')
    for x in range(3, 37):
        c.put(x, 4, wd[4]); c.put(x, 5, wd[3]); c.put(x, 6, wd[3]); c.put(x, 7, wd[2]); c.put(x, 8, wd[1])
        if x % 9 == 0: c.put(x, 6, wd[1])
    c.vline(37, 4, 8, wd[2]); c.vline(38, 5, 8, wd[1]); c.put(37, 6, wd[0])
    _outline_fams(c, [wd])
    return _sprite('beam', c, 20, 10, shadow=(17, 2, 1, 1), tags=('prop', 'ysort'), contact=(15, 1.2), ground_blend=True)


def lantern_hanging():
    """A small iron lantern hanging from a bracket, warm glass."""
    W, H = 12, 18
    c = Canvas(W, H); mt = R('metal'); lg = R('lantern_glass')
    c.hline(1, 8, 2, mt[2]); c.put(8, 3, mt[1]); c.put(8, 4, mt[2])
    lx, ly = 8, 6
    c.hline(lx - 2, lx + 2, ly, mt[2])
    for y in range(ly + 1, ly + 6):
        c.put(lx - 2, y, mt[1]); c.put(lx + 2, y, mt[1])
        for x in range(lx - 1, lx + 2): c.put(x, y, lg[3] if x == lx and ly + 2 <= y <= ly + 3 else lg[2] if x == lx - 1 else lg[1])
    c.hline(lx - 2, lx + 2, ly + 6, mt[2])
    return _sprite('lantern_hanging', c, 5, 16, shadow=None, tags=('prop', 'light'))


# ---------------------------------------------------------------------------------------------------------------- highland
def ledge(name, seed, w=44, h=26, mossy=False):
    """A rock outcrop: several blocks of the same stone pushed up out of the ground and leaning together, the big ones
    behind and higher, smaller split-off pieces in front; planes lit from the upper left, moss on the tops of the
    shaded ones, scree at the foot. Built from the same faceted stones as the camp's rocks, so it is one geology."""
    W, H = w + 8, h + 8
    c = Canvas(W, H); rng = random.Random(seed)
    base = H - 3
    pieces = []
    n = 4 + int(w / 18)
    for k in range(n):
        u = (k + 0.5) / n
        x = 4 + u * w + rng.uniform(-3, 3)
        back = 0.5 + 0.5 * math.sin(u * math.pi)                           # the middle stands tallest
        rx = rng.uniform(0.18, 0.26) * w * (0.8 + 0.4 * back); ry = rx * rng.uniform(0.8, 1.05)
        y = base - ry * 0.62 - back * h * 0.22
        pieces.append((x, y, rx, ry))
    for k in range(n - 1):                                                  # a front row of smaller, lower pieces
        if rng.random() < 0.4: continue
        x = 4 + (k + 1) / n * w + rng.uniform(-2, 2); rx = rng.uniform(0.09, 0.13) * w; ry = rx * 0.75
        pieces.append((x, base - ry * 0.62, rx, ry))
    for i, (x, y, rx, ry) in enumerate(sorted(pieces, key=lambda q: q[1] + q[3] * 0.6)):
        faceted(c, x, y, rx, ry, seed=seed * 13 + i, top_t=4 if i % 3 else 5, mossy=mossy and i % 2 == 0)
    for k in range(4): faceted(c, rng.choice((rng.randint(2, 8), rng.randint(W - 9, W - 3))), base - 1, rng.uniform(1.4, 2.4), rng.uniform(1.0, 1.6), seed=seed + 50 + k, top_t=4)
    return _sprite(name, c, W // 2, base + 1, shadow=(int(w * 0.52), 3, 3, 0), soft_shadow=True, tags=('rock', 'ysort', 'solid'), contact=(w * 0.46, 1.6), ground_blend=True)


def heather(name, seed):
    """Heather: a low cushion of fine dark shoots dotted with tiny pink-purple bells."""
    W, H = 16, 9
    c = Canvas(W, H); rd = R('reed'); fp = R('flower_p'); rng = random.Random(seed)
    lit_blob(c, 8, 5.5, 6.5, 3.2, R('shrub'), seed=seed, rough=0.6, lo=0, hi=2, outline=False)
    for k in range(14):
        x, y = rng.randint(2, 13), rng.randint(2, 6)
        if c.get(x, y): c.put(x, y, fp[1] if rng.random() < 0.6 else fp[2])
    sel_outline(c, c.a != 0, R('shrub'))
    return _sprite(name, c, 8, 8, shadow=None, tags=('plant', 'ysort'))


def leaf_heap(name, seed):
    """Autumn: a drift of fallen leaves banked against something, single leaves skittering off its edge."""
    W, H = 18, 8
    c = Canvas(W, H); ll = R('leaf_litter'); rng = random.Random(seed)
    lit_blob(c, 9, 5, 7, 2.6, ll, seed=seed, rough=0.7, lo=0, hi=3, outline=False)
    for k in range(10):
        x, y = rng.randint(1, 16), rng.randint(2, 6)
        if c.get(x, y): c.put(x, y, ll[3] if rng.random() < 0.5 else ll[1])
    for (x, y) in ((1, 6), (16, 5), (14, 7)): c.put(x, y, ll[2])
    return _sprite(name, c, 9, 7, shadow=None, tags=('ground_plant', 'ysort'))


def add_world_art(lib):
    for s in (cattails('reeds_0', 1), cattails('reeds_1', 2, 7, 24), cattails('cattail_tall', 3, 12, 34),
              lily('lily_0', 1, 6.0), lily('lily_1', 2, 5.0, 'flower_p'), lily('lily_2', 3, 4.0), lily('lily_3', 4, 5.2, 'flower_w'),
              arrowhead('arrowhead_0', 1), arrowhead('arrowhead_1', 2), sedge('sedge_0', 1), sedge('sedge_1', 2, 10), sedge('marsh_grass', 3, 14, 'grass'),
              tuft('tuft_0', 1), tuft('tuft_1', 2, 6), tuft('tuft_2', 3, 8), glowcaps('glowshroom_0', 1), glowcaps('glowshroom_1', 2),
              hollow_log('hollowlog_0', 3), branch('branch_0', 1), branch('branch_1', 2), root_plate('roots_1', 4),
              dock(), bridge(), fence('fence_3', 1, 3), fence('fence_2', 2, 2), signpost(),
              ruin_back(), ruin_side(), ruin_wall(), rubble('rubble_0', 1), rubble('rubble_1', 2), beam(), lantern_hanging(),
              ledge('ledge_0', 1), ledge('ledge_1', 2, 36, 20, mossy=True), ledge('ledge_2', 3, 54, 30), heather('heather_0', 1), heather('heather_1', 2), leaf_heap('leaf_heap_0', 1), leaf_heap('leaf_heap_1', 2)):
        lib[s.name] = s
    return lib
