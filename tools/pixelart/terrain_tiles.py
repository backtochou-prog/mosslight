"""MOSSlight terrain material library.

Every ground material is a *dual-grid* transition set: 15 corner masks x 4
phase variants. The boundary inside a tile is the 0.5 iso-line of a bilinear
corner blend plus one seamless 32-px periodic wobble shared by every material,
so edges are continuous across tile borders and a material always covers the
material beneath it exactly.

Materials declare an `under` material. A material is painted on top of its
`under` chain only (never on top of unrelated layers), which is what makes
"pebbles inside a dirt path", "moss on stone", "deep water inside shallow
water" and "snow over anything" behave: holes in a soft edge reveal exactly
the surface that should be there.

Edge styles (how a material meets what is beneath it):
  soft   - two dithered rings (worn grass, forest floor, sand, mud, pebbles, packed earth, deep water)
  rim    - defined edge: shadowed rim, blades overhanging from above, lit lower edge (dirt)
  ledge  - raised stone: lit north edge, dark south face, moss at the foot (stone, mossy stone)
  clip   - flagstones clipped to whole slabs, grass creeping into joints (paved)
  shore  - water meets earth: dark far-bank line, reflection, light lapping line (shallow water)
  drift  - snow: soft edge with a lit crest on the upper-left and a cool shadow on the lower-right
"""
from __future__ import annotations
import random, json, os
from dataclasses import dataclass
import numpy as np
from .canvas import Canvas
from .palette import PAL
from .noise import value_noise

T = 16

@dataclass(frozen=True)
class Material:
    id: int
    name: str
    under: int | None
    edge: str
    label: str

MATERIALS: list[Material] = [
    Material(0,  'grass',   None, 'none',  'lush grass'),
    Material(1,  'worn',    0,    'soft',  'short worn grass'),
    Material(2,  'forest',  0,    'soft',  'dense forest ground'),
    Material(3,  'sand',    0,    'soft',  'sandy ground'),
    Material(4,  'dirt',    0,    'rim',   'soft dirt'),
    Material(5,  'earth',   4,    'soft',  'packed earth'),
    Material(6,  'pebble',  4,    'soft',  'pebbled path'),
    Material(7,  'mud',     0,    'soft',  'mud / wet bank'),
    Material(8,  'stone',   0,    'ledge', 'natural stone'),
    Material(9,  'mossy',   8,    'ledge', 'moss-covered stone'),
    Material(10, 'paved',   4,    'clip',  'flagstone paving'),
    Material(11, 'shallow', 0,    'shore', 'shallow water'),
    Material(12, 'water',   11,   'soft',  'deep water'),
]
GRASS, WORN, FOREST, SAND, DIRT, EARTH, PEBBLE, MUD, STONE, MOSSY, PAVED, SHALLOW, WATER = range(13)
# snow is an overlay grid, not a ground material: 1 = snow, 2 = trampled snow path
SNOW, SNOW_PATH = 1, 2
LAYER_NAMES = [m.name for m in MATERIALS]
BY_NAME = {m.name: m for m in MATERIALS}

def ancestors(mid: int) -> list[int]:
    out = []
    m = MATERIALS[mid]
    while m is not None:
        out.append(m.id)
        m = MATERIALS[m.under] if m.under is not None else None
    return out

_ANC = [set(ancestors(i)) for i in range(len(MATERIALS))]
def covers(corner_mat: int, layer: int) -> bool:
    """True if `layer` must be painted under a corner of material `corner_mat`."""
    return layer in _ANC[corner_mat]

# ---------------------------------------------------------------------------
# edge geometry (shared by every material)
# ---------------------------------------------------------------------------
WOBBLE, WSEED = 0.17, 11

def coverage(mask_bits, px, py, phase):
    tl, tr, bl, br = mask_bits
    u, v = (px + 0.5) / T, (py + 0.5) / T
    f = (tl * (1 - u) + tr * u) * (1 - v) + (bl * (1 - u) + br * u) * v
    gx, gy = px + phase[0] * T, py + phase[1] * T
    w = (value_noise(gx, gy, 6.0, WSEED, period=32) - 0.5) * 2 * WOBBLE
    w += (value_noise(gx, gy, 3.0, WSEED + 5, period=32) - 0.5) * WOBBLE * 0.6
    return f + w

_MASK_CACHE = {}
def layer_mask(bits, phase):
    key = (bits, phase)
    if key not in _MASK_CACHE:
        m = np.zeros((T, T), dtype=bool)
        for y in range(T):
            for x in range(T):
                m[y, x] = coverage(bits, x, y, phase) > 0.5
        _MASK_CACHE[key] = m
    return _MASK_CACHE[key]

def rim(m):
    p = np.pad(m, 1, constant_values=True)
    up = m & ~p[:-2, 1:-1]; down = m & ~p[2:, 1:-1]
    left = m & ~p[1:-1, :-2]; right = m & ~p[1:-1, 2:]
    return (up | down | left | right), up, down, left, right

def inner_ring(m, k):
    """Pixels of m at 4-neighbour distance exactly k from the outside."""
    cur = m.copy(); rings = []
    for _ in range(k):
        p = np.pad(cur, 1, constant_values=True)
        inner = cur & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
        rings.append(cur & ~inner); cur = inner
    return rings[k - 1] if rings else np.zeros_like(m)

# ---------------------------------------------------------------------------
# base textures (16x16, periodic)
# ---------------------------------------------------------------------------
def _marks(c, rng, fam, base, n_dark, n_light, dark_len=2):
    for _ in range(n_dark):
        x, y = rng.randrange(T), rng.randrange(T)
        for k in range(rng.randint(1, dark_len)): c.put((x + k) % T, y, PAL.i(fam, base - 1))
    for _ in range(n_light):
        x, y = rng.randrange(T), rng.randrange(T)
        c.put(x, y, PAL.i(fam, base + 1))

def grass_tile(variant: int, shade: str) -> Canvas:
    rng = random.Random(1000 + variant * 7 + hash(shade) % 97)
    c = Canvas(T, T); base = 3
    c.rect(0, 0, T, T, PAL.i('grass', base))
    n_light = {'dark': 1, 'mid': 2, 'sun': 3}[shade]; n_dark = {'dark': 3, 'mid': 2, 'sun': 1}[shade]
    for _ in range(n_light):                      # a tuft: three lit blade tips over a dark root
        x, y = rng.randrange(T), rng.randrange(T)
        c.put(x, (y - 1) % T, PAL.i('grass', base + 1)); c.put((x + 2) % T, (y - 1) % T, PAL.i('grass', base + 1))
        c.put((x + 1) % T, y, PAL.i('grass', base + 1)); c.put((x + 1) % T, (y - 2) % T, PAL.i('grass', base + 2) if shade == 'sun' else PAL.i('grass', base + 1))
        c.put((x + 1) % T, (y + 1) % T, PAL.i('grass', base - 1))
    for _ in range(n_dark):                       # a shaded pocket
        x, y = rng.randrange(T), rng.randrange(T)
        c.put(x, y, PAL.i('grass', base - 1)); c.put((x + 1) % T, y, PAL.i('grass', base - 1))
    if shade == 'sun' and rng.random() < 0.6:
        x, y = rng.randrange(T), rng.randrange(T)
        c.put(x, y, PAL.i('grass', 5)); c.put(x, (y + 1) % T, PAL.i('grass', 4))
    if variant == 5:
        x, y = rng.randrange(T), rng.randrange(T)
        for dx, dy in ((0, 0), (1, 0), (0, 1), (-1, 0), (0, -1)):
            c.put((x + dx) % T, (y + dy) % T, PAL.i('grass', base - 1 if (dx, dy) == (0, 0) else base + 1))
    return c

def _pebble(c, x, y, big=False):
    pb = PAL.ramp('pebble')
    c.put(x % T, y % T, pb[1]); c.put((x + 1) % T, y % T, pb[0])
    if big:
        c.put(x % T, (y - 1) % T, pb[1]); c.put((x + 1) % T, (y - 1) % T, pb[1]); c.put((x + 2) % T, y % T, pb[0]); c.put((x + 1) % T, (y - 2) % T, pb[2])
    elif random.random() < 0.35:
        c.put(x % T, (y - 1) % T, pb[2])

def base_texture(mat: int, phase) -> Canvas:
    rng = random.Random(500 + mat * 31 + phase[0] * 3 + phase[1] * 5)
    random.seed(rng.random())
    c = Canvas(T, T)
    name = MATERIALS[mat].name
    if name == 'worn':
        c.rect(0, 0, T, T, PAL.i('worn', 2)); _marks(c, rng, 'worn', 2, 2, 2)
        for _ in range(5):
            x, y = rng.randrange(T), rng.randrange(T)
            c.put(x, y, PAL.i('grass', 3)); c.put((x + 1) % T, y, PAL.i('grass', 3))
    elif name == 'forest':
        c.rect(0, 0, T, T, PAL.i('forest', 2)); _marks(c, rng, 'forest', 2, 4, 3)
        if rng.random() < 0.6:
            x, y = rng.randrange(T), rng.randrange(T)
            c.put(x, y, PAL.i('leaf_litter', 1)); c.put((x + 1) % T, y, PAL.i('leaf_litter', 2))
    elif name == 'sand':
        c.rect(0, 0, T, T, PAL.i('sand', 3)); _marks(c, rng, 'sand', 3, 2, 3, 1)
        if rng.random() < 0.7:                           # a soft ripple
            x, y = rng.randrange(T), rng.randrange(T)
            for k in range(4): c.put((x + k) % T, (y + (k // 2)) % T, PAL.i('sand', 2))
    elif name == 'dirt':
        c.rect(0, 0, T, T, PAL.i('dirt', 3)); _marks(c, rng, 'dirt', 3, 2, 1, 3)
        if rng.random() < 0.5:
            x, y = rng.randrange(T), rng.randrange(T)
            for dx in range(-2, 3):
                for dy in range(-1, 2):
                    if abs(dx) + abs(dy) < 3 and (dx + dy) % 2 == 0: c.put((x + dx) % T, (y + dy) % T, PAL.i('dirt', 2))
        if rng.random() < 0.5: _pebble(c, rng.randrange(T), rng.randrange(T))
    elif name == 'earth':
        c.rect(0, 0, T, T, PAL.i('earth', 3)); _marks(c, rng, 'earth', 3, 1, 1, 2)
        x, y = rng.randrange(T), rng.randrange(T)        # a hairline crack
        for k in range(rng.randint(3, 6)):
            c.put((x + k) % T, (y + (k % 3 == 2)) % T, PAL.i('earth', 1))
    elif name == 'pebble':
        c.rect(0, 0, T, T, PAL.i('dirt', 3)); _marks(c, rng, 'dirt', 3, 1, 1, 2)
        for _ in range(rng.randint(2, 3)):
            _pebble(c, rng.randrange(T), rng.randrange(T), big=rng.random() < 0.3)
    elif name == 'mud':
        c.rect(0, 0, T, T, PAL.i('mud', 2)); _marks(c, rng, 'mud', 2, 2, 1, 2)
        for _ in range(3):
            x, y = rng.randrange(T), rng.randrange(T)
            c.put(x, y, PAL.i('grass', 2)); c.put(x, (y - 1) % T, PAL.i('grass', 3))
        if rng.random() < 0.6: c.put(rng.randrange(T), rng.randrange(T), PAL.i('pebble', 0))
        if rng.random() < 0.5:                           # wet gleam
            x, y = rng.randrange(T), rng.randrange(T)
            c.put(x, y, PAL.i('mud', 3)); c.put((x + 1) % T, y, PAL.i('mud', 3))
    elif name in ('stone', 'mossy'):
        sheet = rock_sheet()
        ox, oy = phase[0] * T, phase[1] * T
        c.a[:, :] = sheet.a[oy:oy + T, ox:ox + T]
        if name == 'mossy':
            mo = PAL.ramp('moss')
            for _ in range(2):
                x, y = rng.randrange(T), rng.randrange(T); rx, ry = rng.randint(2, 3), rng.randint(1, 2)
                for dx in range(-rx - 1, rx + 2):
                    for dy in range(-ry - 1, ry + 2):
                        d = (dx / (rx + 0.5)) ** 2 + (dy / (ry + 0.5)) ** 2
                        if d <= 1: c.put((x + dx) % T, (y + dy) % T, mo[2] if (dx - dy) % 3 == 0 and d < 0.5 else mo[1])
                        elif d <= 1.7 and (dx + dy) % 2 == 0: c.put((x + dx) % T, (y + dy) % T, mo[0])
    elif name == 'paved':
        c.rect(0, 0, T, T, PAL.i('dirt', 2))
    elif name == 'shallow':
        c.rect(0, 0, T, T, PAL.i('water', 2))
        for _ in range(3):                               # sandy bottom showing through
            x, y = rng.randrange(T), rng.randrange(T)
            if (x + y) % 2 == 0: c.put(x, y, PAL.i('water', 3))
        x, y = rng.randrange(T), rng.randrange(T)        # ripple
        for k in range(3): c.put((x + k) % T, y, PAL.i('water', 4 if k == 1 else 3))
    elif name == 'water':
        c.rect(0, 0, T, T, PAL.i('water', 1))
        if rng.random() < 0.5:
            x, y = rng.randrange(T), rng.randrange(T)
            for k in range(3): c.put((x + k) % T, y, PAL.i('water', 2))
    return c

def snow_texture(kind: int, phase) -> Canvas:
    rng = random.Random(700 + kind * 17 + phase[0] * 3 + phase[1] * 5)
    c = Canvas(T, T); sn = PAL.ramp('snow')
    if kind == SNOW:
        c.rect(0, 0, T, T, sn[3])
        for _ in range(2):                               # soft blue dip
            x, y = rng.randrange(T), rng.randrange(T)
            c.put(x, y, sn[2]); c.put((x + 1) % T, y, sn[2]); c.put((x + 2) % T, (y + 1) % T, sn[2])
        if rng.random() < 0.7: c.put(rng.randrange(T), rng.randrange(T), sn[4])    # sparkle
    else:
        c.rect(0, 0, T, T, sn[2])
        for _ in range(3):                               # trampled dashes
            x, y = rng.randrange(T), rng.randrange(T)
            c.put(x, y, sn[1]); c.put((x + 1) % T, y, sn[1])
        if rng.random() < 0.6:                           # exposed earth
            x, y = rng.randrange(T), rng.randrange(T)
            c.put(x, y, PAL.i('earth', 2)); c.put((x + 1) % T, y, PAL.i('earth', 1))
        c.put(rng.randrange(T), rng.randrange(T), sn[3])
    return c

# ---------------------------------------------------------------------------
# flagstones (32x32 torus)
# ---------------------------------------------------------------------------
_SLABS = [  # (x, y, w, h, rank) rounded slabs on a 32x32 torus, 1-px joints
    (0, 0, 10, 7, 3), (11, 0, 9, 8, 2), (21, 0, 11, 6, 3),
    (0, 8, 7, 9, 2), (8, 9, 12, 7, 3), (21, 7, 11, 9, 2),
    (0, 18, 11, 8, 3), (12, 17, 8, 9, 2), (21, 17, 11, 8, 3),
    (0, 27, 9, 5, 2), (10, 27, 10, 5, 3), (21, 26, 11, 6, 2),
]
_ROCKSHEET = None
def rock_sheet():
    """32x32 periodic fractured bedrock: a crack network (dark) with a lit
    facet edge on the upper-left side of every crack and a shaded one on the
    lower-right, so slabs read as faceted rock, not as a grey smudge."""
    global _ROCKSHEET
    if _ROCKSHEET is not None: return _ROCKSHEET
    rng = random.Random(77); st = PAL.ramp('stone')
    c = Canvas(32, 32); c.rect(0, 0, 32, 32, st[3])
    crack = np.zeros((32, 32), dtype=bool)
    for _ in range(4):
        x, y = rng.randrange(32), rng.randrange(32)
        dx = 1; dy = rng.choice((0, 0, 1, -1)) * 0.5
        fy = float(y)
        for k in range(rng.randint(12, 22)):
            crack[int(round(fy)) % 32, x % 32] = True
            if rng.random() < 0.15: dy = rng.choice((0, 0.5, -0.5))
            x += dx; fy += dy
    ys, xs = np.nonzero(crack)
    for k in range(len(xs)):
        x, y = int(xs[k]), int(ys[k])
        c.put(x, y, st[1])
        if not crack[(y - 1) % 32, x]: c.put(x, (y - 1) % 32, st[4])
        if not crack[(y + 1) % 32, x]: c.put(x, (y + 1) % 32, st[2])
    for _ in range(5):                                        # subtle lighter facets
        x, y = rng.randrange(32), rng.randrange(32)
        for dx in range(3):
            for dy in range(2):
                if not crack[(y + dy) % 32, (x + dx) % 32] and c.get((x + dx) % 32, (y + dy) % 32) == st[3]: c.put((x + dx) % 32, (y + dy) % 32, st[4])
    for _ in range(4):
        x, y = rng.randrange(32), rng.randrange(32)
        if c.get(x, y) == st[3]: c.put(x, y, st[2])
    _ROCKSHEET = c
    return _ROCKSHEET

_FLAGSHEET = None
def flag_sheet():
    """Slabs: rounded rectangles, lit top row, dark bottom/right edge, a crack or two."""
    global _FLAGSHEET
    if _FLAGSHEET is not None: return _FLAGSHEET
    c = Canvas(32, 32); ids = np.zeros((32, 32), dtype=np.int16)
    c.rect(0, 0, 32, 32, PAL.i('dirt', 2))
    rng = random.Random(3)
    for k, (x, y, w, h, rank) in enumerate(_SLABS, start=1):
        m = np.zeros((32, 32), dtype=bool)
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                corner = (xx in (x, x + w - 1)) and (yy in (y, y + h - 1))
                if not corner: m[yy % 32, xx % 32] = True
        ids[m] = k
        c.a[m] = PAL.i('stone', rank)
        p = np.pad(m, 1)
        top = m & ~p[:-2, 1:-1]; bot = m & ~p[2:, 1:-1]; right = m & ~p[1:-1, 2:]
        c.a[top] = PAL.i('stone', rank + 1); c.a[bot | right] = PAL.i('stone', rank - 1)
        if rng.random() < 0.5:
            cx, cy = x + rng.randint(2, w - 3), y + rng.randint(1, h - 2)
            for s in range(rng.randint(2, 4)):
                if m[(cy + (s // 2)) % 32, (cx + s) % 32]: c.a[(cy + (s // 2)) % 32, (cx + s) % 32] = PAL.i('stone', rank - 1)
        if rng.random() < 0.4:
            c.a[bot & (np.indices(m.shape)[1] % 3 == k % 3)] = PAL.i('moss', 1)
    _FLAGSHEET = (c, ids)
    return _FLAGSHEET

# ---------------------------------------------------------------------------
# transition tiles
# ---------------------------------------------------------------------------
def soft_edge(c, m, rng, rings=2):
    edge, *_ = rim(m)
    r2 = inner_ring(m, 2); r3 = inner_ring(m, 3)
    for y in range(T):
        for x in range(T):
            if edge[y, x] and ((x + y) % 2 == 0 or rng.random() < 0.25): c.a[y, x] = 0
            elif rings > 1 and r2[y, x] and rng.random() < 0.3: c.a[y, x] = 0
            elif rings > 2 and r3[y, x] and (x + y) % 2 == 0 and rng.random() < 0.35: c.a[y, x] = 0

def transition_tile(mat: int, bits, phase) -> Canvas:
    full = all(bits)
    m = np.ones((T, T), dtype=bool) if full else layer_mask(bits, phase)
    rng = random.Random(900 + phase[0] * 11 + phase[1] * 13 + sum(b << i for i, b in enumerate(bits)))
    c = base_texture(mat, phase); c.a[~m] = 0
    edge, up, down, left, right = rim(m)
    style = MATERIALS[mat].edge
    name = MATERIALS[mat].name
    if style == 'soft':
        soft_edge(c, m, rng, rings=3 if name == 'water' else 2)
        if name == 'mud': c.scatter(rng, m & ~edge, 3, PAL.i('mud', 1), clump=1)
        if name == 'pebble':                                   # pebbles spill past the soft edge
            ys, xs = np.nonzero(edge)
            for _ in range(2):
                if len(xs):
                    k = rng.randrange(len(xs)); _pebble(c, int(xs[k]), int(ys[k]))
    elif style == 'rim':
        c.a[edge] = PAL.i('dirt', 2); c.a[up] = PAL.i('dirt', 1)
        ys, xs = np.nonzero(up)
        for k in range(len(xs)):
            if rng.random() < 0.35:
                x, y = int(xs[k]), int(ys[k]); c.put(x, y, PAL.i('grass', 2))
                if rng.random() < 0.5 and m[min(T - 1, y + 1), x]: c.put(x, y + 1, PAL.i('grass', 1))
        c.a[down & ~up] = PAL.i('dirt', 3)
        ys, xs = np.nonzero(edge)
        for _ in range(2):
            if len(xs):
                k = rng.randrange(len(xs)); x, y = int(xs[k]), int(ys[k])
                if m[y, x]: c.put(x, y, PAL.i('pebble', 1))
    elif style == 'ledge':
        st = PAL.ramp('stone'); mo = PAL.ramp('moss')
        c.a[left] = st[4]; c.a[up] = st[4]
        c.a[right] = st[1]
        c.a[down] = st[0]
        r2 = inner_ring(m, 2); r3 = inner_ring(m, 3)
        p = np.pad(down, ((0, 1), (0, 0)))[1:, :]                # rows above the south edge: side face
        q = np.pad(p, ((0, 1), (0, 0)))[1:, :]
        c.a[r2 & p] = st[1]
        c.a[r3 & q] = st[2]
        # moss / grass at the foot of the ledge (shaded, damp)
        ys, xs = np.nonzero(down | right)
        for k in range(len(xs)):
            if rng.random() < (0.5 if name == 'mossy' else 0.22):
                c.put(int(xs[k]), int(ys[k]), mo[1] if rng.random() < 0.7 else mo[0])
        # grass creeping onto the north edge
        ys, xs = np.nonzero(up | left)
        for k in range(len(xs)):
            if rng.random() < 0.12: c.put(int(xs[k]), int(ys[k]), PAL.i('grass', 3))
    elif style == 'clip':
        sheet, ids = flag_sheet()
        ox, oy = phase[0] * T, phase[1] * T
        sub_ids = ids[oy:oy + T, ox:ox + T]; sub_px = sheet.a[oy:oy + T, ox:ox + T]
        keep = np.zeros((T, T), dtype=bool)
        for sid in np.unique(sub_ids):
            if sid == 0: continue
            cell = sub_ids == sid
            if np.all(m[cell]): keep |= cell
        c.a[keep] = sub_px[keep]
        gapm = (sub_px == PAL.i('dirt', 2)) & m & ~keep
        c.a[gapm] = PAL.i('dirt', 2)
        joints = m & ~keep
        c.scatter(rng, joints, 2, PAL.i('moss', 1), clump=1)
        if not full:                                           # grass reclaiming the edge joints
            ys, xs = np.nonzero(joints & (inner_ring(m, 1) | inner_ring(m, 2)))
            for k in range(len(xs)):
                if rng.random() < 0.3:
                    c.put(int(xs[k]), int(ys[k]), PAL.i('grass', 3))
                    if rng.random() < 0.5: c.put(int(xs[k]), int(ys[k]) - 1, PAL.i('grass', 4))
    elif style == 'shore':
        # a wet bank 2-3 px wide inside the water's edge, then the water line
        wr = PAL.ramp('water'); md = PAL.ramp('mud')
        r1, r2, r3, r4 = inner_ring(m, 1), inner_ring(m, 2), inner_ring(m, 3), inner_ring(m, 4)
        if not full:
            idx = np.indices(m.shape)
            bank = r1 | r2 | (r3 & ((idx[0] + idx[1]) % 2 == 0))
            c.a[bank] = md[2]
            c.a[r1 & ((idx[0] * 3 + idx[1]) % 5 == 0)] = md[1]
            c.a[r1 & ((idx[0] + idx[1] * 7) % 6 == 0)] = PAL.i('grass', 2)
            waterline = (r3 & ~bank) | r4
            c.a[waterline] = wr[2]
            c.a[r3 & ~bank] = wr[3]
            # far bank shadows the water; near bank catches light
            upm = np.pad(up, ((0, 3), (0, 0)))[3:, :] | np.pad(up, ((0, 4), (0, 0)))[4:, :]
            c.a[waterline & upm] = wr[1]
            dnm = np.pad(down, ((3, 0), (0, 0)))[:-3, :] | np.pad(down, ((4, 0), (0, 0)))[:-4, :]
            c.a[waterline & dnm] = wr[4]
    return c

def snow_tile(kind: int, bits, phase) -> Canvas:
    full = all(bits)
    m = np.ones((T, T), dtype=bool) if full else layer_mask(bits, phase)
    rng = random.Random(1300 + kind * 7 + phase[0] * 11 + phase[1] * 13 + sum(b << i for i, b in enumerate(bits)))
    c = snow_texture(kind, phase); c.a[~m] = 0
    edge, up, down, left, right = rim(m)
    sn = PAL.ramp('snow')
    soft_edge(c, m, rng, rings=1)
    keep = c.a != 0
    c.a[(up | left) & keep] = sn[4] if kind == SNOW else sn[3]
    c.a[(down | right) & ~(up | left) & keep] = sn[1]
    r2 = inner_ring(m, 2)
    c.a[r2 & np.pad(down, ((0, 1), (0, 0)))[1:, :] & keep] = sn[2] if kind == SNOW else sn[1]
    return c

ALL_MASKS = [(tl, tr, bl, br) for tl in (0, 1) for tr in (0, 1) for bl in (0, 1) for br in (0, 1)]
PHASES = [(0, 0), (1, 0), (0, 1), (1, 1)]
def mask_code(bits):
    tl, tr, bl, br = bits
    return tl | (tr << 1) | (bl << 2) | (br << 3)

class TerrainTiles:
    """Builds and caches every terrain tile; exports atlases + materials.json."""
    def __init__(self):
        self.grass = {s: [grass_tile(v, s) for v in range(6)] for s in ('dark', 'mid', 'sun')}
        self.trans = {}
        for mat in range(1, len(MATERIALS)):
            for bits in ALL_MASKS:
                if not any(bits): continue
                for ph in PHASES:
                    self.trans[(mat, mask_code(bits), ph)] = transition_tile(mat, bits, ph)
        self.snow = {}
        for kind in (SNOW, SNOW_PATH):
            for bits in ALL_MASKS:
                if not any(bits): continue
                for ph in PHASES:
                    self.snow[(kind, mask_code(bits), ph)] = snow_tile(kind, bits, ph)

    def export(self, out_dir):
        meta = {'tile_size': T, 'edge_geometry': 'shared 32px periodic wobble; mask code tl|tr<<1|bl<<2|br<<3; rows = phase (tx%2, ty%2)',
                'grass': {'file': 'terrain_grass.png', 'rows': ['dark', 'mid', 'sun'], 'variants': 6}, 'materials': [], 'snow': {}}
        g = Canvas(6 * T, 3 * T)
        for r, s in enumerate(('dark', 'mid', 'sun')):
            for v in range(6): g.blit(self.grass[s][v], v * T, r * T)
        g.save(os.path.join(out_dir, 'terrain_grass.png'))
        for mat in MATERIALS:
            entry = {'id': mat.id, 'name': mat.name, 'label': mat.label, 'under': mat.under, 'edge': mat.edge}
            if mat.id > 0:
                a = Canvas(16 * T, 4 * T)
                for code in range(1, 16):
                    for pi, ph in enumerate(PHASES): a.blit(self.trans[(mat.id, code, ph)], code * T, pi * T)
                entry['file'] = f'terrain_{mat.name}.png'
                a.save(os.path.join(out_dir, entry['file']))
            meta['materials'].append(entry)
        for kind, nm in ((SNOW, 'snow'), (SNOW_PATH, 'snow_path')):
            a = Canvas(16 * T, 4 * T)
            for code in range(1, 16):
                for pi, ph in enumerate(PHASES): a.blit(self.snow[(kind, code, ph)], code * T, pi * T)
            a.save(os.path.join(out_dir, f'terrain_{nm}.png')); meta['snow'][nm] = {'file': f'terrain_{nm}.png', 'kind': kind}
        for stale in ('terrain_litter.png',):
            if os.path.exists(os.path.join(out_dir, stale)): os.remove(os.path.join(out_dir, stale))
        with open(os.path.join(out_dir, 'materials.json'), 'w') as f: json.dump(meta, f, indent=1)
        old = os.path.join(out_dir, 'terrain_tiles.json')
        if os.path.exists(old): os.remove(old)
        return meta
