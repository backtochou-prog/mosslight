"""PixelLab terrain: the ground is painted from Wang tilesets generated with PixelLab (create_topdown_tileset, pro mode,
16 px, on the game's palette), all chained onto one approved grass tile so every set shares the same grass.

The material map already works on a dual grid (materials live on tile corners), which is exactly how a Wang set is
indexed: each 16 px cell picks the tile whose four corners match. Materials fold into four ground classes:

    g  grass                         the 'upper' terrain of every set
    s  deeper, cooler grass (worn, painted as patches)  -> ts_grass_shade3: shade and drifts; quiet light grass between
    d  dirt  (dirt, earth, pebble, paved, sand, mud)  -> ts_grass_dirt2
    f  forest floor                                   -> ts_grass_forest2
    w  water (shallow, deep)                          -> ts_water_grass2

A cell whose corners mix more than one non-grass class takes the strongest one (water over dirt over forest) and
treats the others as grass, so every cell is a real tile from a real set, never a patched hybrid.
"""
from __future__ import annotations
import os, json
import numpy as np
from PIL import Image
from .canvas import Canvas
from .terrain_tiles import T, GRASS, WORN, FOREST, SAND, DIRT, EARTH, PEBBLE, MUD, STONE, MOSSY, PAVED, SHALLOW, WATER
from .pl_pilot import to_palette, despeckle

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'assets/pixellab/src')
SETS = {'d': 'ts_grass_dirt3', 'f': 'ts_grass_forest3', 'w': 'ts_water_grass3', 's': 'ts_grass_shade3'}      # the calm sets (basic shading, low detail): the first ones read as pixel noise
FAMS = {'s': ('grass',), 'd': ('dirt', 'grass', 'earth'), 'f': ('forest', 'leaf_litter', 'grass', 'moss'), 'w': ('water', 'grass', 'mud', 'sand')}
CLASS = {GRASS: 'g', WORN: 's', DIRT: 'd', EARTH: 'd', PEBBLE: 'd', PAVED: 'd', SAND: 'd', MUD: 'd', FOREST: 'f', SHALLOW: 'w', WATER: 'w', STONE: 'g', MOSSY: 'g'}
PRIORITY = ('w', 'd', 'f', 's')

_CACHE = None


def _bright(v):
    from .palette import PAL
    return sum(PAL.day[int(v)][:3])


def unhatch(c, dark, light):
    """The dark/light grass transitions came hatched with diagonal dither lines. Each pixel in the hatched band is decided
    by the majority of its 5x5 neighbourhood (dark or light) and painted in one of the two plain greens: a clean, gently
    wobbling edge instead of hatching. Quiet interiors keep their own marks."""
    a = c.a; th = (_bright(dark) + _bright(light)) / 2
    lut = {int(v): _bright(v) < th for v in np.unique(a)}
    d = np.vectorize(lambda v: float(lut[int(v)]))(a)
    p = np.pad(d, 2, mode='edge'); h, w = a.shape
    acc = sum(p[2 + dy:2 + dy + h, 2 + dx:2 + dx + w] for dy in range(-2, 3) for dx in range(-2, 3)) / 25.0
    out = c.copy(); band = (acc > 0.12) & (acc < 0.88)
    out.a[band & (acc >= 0.5)] = dark; out.a[band & (acc < 0.5)] = light
    return out


def available():
    return all(os.path.exists(os.path.join(SRC, s, 'sheet.png')) for s in SETS.values())


def load_sets():
    """{class: {(NW, NE, SW, SE) as 'u'/'l': Canvas}}, plus the grass fill under key 'g'."""
    global _CACHE
    if _CACHE: return _CACHE
    out = {}
    for k, name in SETS.items():
        sheet = np.array(Image.open(os.path.join(SRC, name, 'sheet.png')).convert('RGBA'))
        meta = json.load(open(os.path.join(SRC, name, 'metadata.json')))
        tiles = {}
        for t in meta['tileset_data']['tiles']:
            bb = t['bounding_box']; c4 = t['corners']
            key = tuple('u' if c4[q] == 'upper' else 'l' for q in ('NW', 'NE', 'SW', 'SE'))
            rgba = sheet[bb['y']:bb['y'] + bb['height'], bb['x']:bb['x'] + bb['width']]
            tiles[key], _ = to_palette(rgba, FAMS[k])
        if k == 's':
            com = lambda c_: (lambda v, n: v[n.argmax()])(*np.unique(c_.a, return_counts=True))
            dark, light = com(tiles[('l', 'l', 'l', 'l')]), com(tiles[('u', 'u', 'u', 'u')])
            for key in tiles:
                tiles[key] = unhatch(tiles[key], dark, light)
        out[k] = tiles
    # quieter grass: the tile's scattered marks repeat every 16 px and read as noise across a meadow, so two marks in
    # three go back to the base green (marks touching another material - the edge of a path or the bank - stay)
    from .palette import PAL
    G = PAL.ramp('grass')
    for k, tiles in out.items():
        for key, c in tiles.items():
            a = c.a; gm = np.isin(a, G)
            if not gm.any(): continue
            p = np.pad(gm, 1, constant_values=True); inner = p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
            pa = np.pad(a, 1, mode='edge'); h, w = a.shape
            nb = np.stack([pa[1 + dy:1 + dy + h, 1 + dx:1 + dx + w] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)])
            same = (nb == a[None]).sum(0)
            ys, xs = np.nonzero(gm & inner & (same <= 2))                  # a mark: a pixel few of its neighbours share (never a tone region)
            for y, x in zip(ys, xs):
                if (x * 7 + y * 13) % 3:
                    v, n = np.unique(nb[:, y, x], return_counts=True); a[y, x] = v[n.argmax()]
    out['g'] = {('u', 'u', 'u', 'u'): out['d'][('u', 'u', 'u', 'u')]}
    _CACHE = out
    return out


def render(mm) -> Canvas:
    """Ground from the Wang sets. The deeper-grass patches are not tile shapes: they are cut from a smooth field
    (the painted patches, bilinear between tile corners, with a gentle wobble) at pixel resolution, so their edges
    are clean and organic; inside them the pixels come from the PixelLab deep-grass tile, outside from the light one."""
    from .palette import PAL
    from .noise import value_noise
    sets = load_sets()
    W, H = mm.w, mm.h
    c = Canvas(W * T, H * T)
    for ty in range(H):
        for tx in range(W):
            cls = [CLASS.get(int(v), 'g') for v in (mm.m[ty, tx], mm.m[ty, tx + 1], mm.m[ty + 1, tx], mm.m[ty + 1, tx + 1])]
            cls = ['g' if k == 's' else k for k in cls]
            others = [k for k in PRIORITY if k in cls]
            if not others: tile = sets['g'][('u', 'u', 'u', 'u')]
            else:
                x = others[0]; tile = sets[x][tuple('l' if k == x else 'u' for k in cls)]
            c.blit(tile, tx * T, ty * T)
    if 's' in sets:
        f = (mm.m == WORN).astype(np.float32)
        from PIL import Image as _I
        big = np.array(_I.fromarray(f, 'F').resize((W * T + 1, H * T + 1), _I.BILINEAR))[:H * T, :W * T]
        yy, xx = np.mgrid[0:H * T, 0:W * T]
        wob = np.vectorize(lambda x, y: value_noise(x, y, 9.0, 41))(xx[::2, ::2], yy[::2, ::2])
        wob = np.repeat(np.repeat(wob, 2, 0), 2, 1)[:H * T, :W * T]
        mask = (big + (wob - 0.5) * 0.45) > 0.5
        dark = sets['s'][('l', 'l', 'l', 'l')].a
        fill = np.tile(dark, (H, W))
        G = PAL.ramp('grass')
        sel = mask & np.isin(c.a, G)
        c.a[sel] = fill[sel]
    return c
