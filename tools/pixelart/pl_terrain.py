"""PixelLab terrain: the ground is painted from Wang tilesets generated with PixelLab (create_topdown_tileset, pro mode,
16 px, on the game's palette), all chained onto one approved grass tile so every set shares the same grass.

The material map already works on a dual grid (materials live on tile corners), which is exactly how a Wang set is
indexed: each 16 px cell picks the tile whose four corners match. Materials fold into four ground classes:

    g  grass                         the 'upper' terrain of every set
    v  deeper grass with clover (ts_grass_clover3): generated, kept out of use for now - its raised lime rim reads as a terrace
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
from .pl_pilot import to_palette

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'assets/pixellab/src')
SETS = {'d': 'ts_grass_dirt3', 'f': 'ts_grass_forest3', 'w': 'ts_water_grass3', 'v': 'ts_grass_clover3'}      # the calm sets (basic shading, low detail): the first ones read as pixel noise
FAMS = {'v': ('grass', 'fern'), 'd': ('dirt', 'grass', 'earth'), 'f': ('forest', 'leaf_litter', 'grass', 'moss'), 'w': ('water', 'grass', 'mud', 'sand')}
CLASS = {GRASS: 'g', WORN: 'g', DIRT: 'd', EARTH: 'd', PEBBLE: 'd', PAVED: 'd', SAND: 'd', MUD: 'd', FOREST: 'f', SHALLOW: 'w', WATER: 'w', STONE: 'g', MOSSY: 'g'}
PRIORITY = ('w', 'd', 'f', 'v')

_CACHE = None


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
        out[k] = tiles
    # quieter grass: the tile's scattered marks repeat every 16 px and read as noise across a meadow, so two marks in
    # three go back to the base green (marks touching another material - the edge of a path or the bank - stay)
    from .palette import PAL
    G = PAL.ramp('grass')
    for k, tiles in out.items():
        for key, c in tiles.items():
            a = c.a; gm = np.isin(a, G)
            if not gm.any(): continue
            vals, cnt = np.unique(a[gm], return_counts=True); base = vals[cnt.argmax()]
            p = np.pad(gm, 1, constant_values=True); inner = p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
            ys, xs = np.nonzero(gm & inner & (a != base))
            for y, x in zip(ys, xs):
                if (x * 7 + y * 13) % 3: a[y, x] = base
    out['g'] = {('u', 'u', 'u', 'u'): out['d'][('u', 'u', 'u', 'u')]}
    _CACHE = out
    return out


def render(mm) -> Canvas:
    sets = load_sets()
    W, H = mm.w, mm.h
    c = Canvas(W * T, H * T)
    for ty in range(H):
        for tx in range(W):
            cls = [CLASS.get(int(v), 'g') for v in (mm.m[ty, tx], mm.m[ty, tx + 1], mm.m[ty + 1, tx], mm.m[ty + 1, tx + 1])]
            others = [k for k in PRIORITY if k in cls]
            if not others:
                tile = sets['g'][('u', 'u', 'u', 'u')]
            else:
                x = others[0]
                key = tuple('l' if k == x else 'u' for k in cls)
                tile = sets[x][key]
            c.blit(tile, tx * T, ty * T)
    return c
