"""PixelLab pilot pack -> game library.

Sources live in assets/pixellab/src/<asset>/cand_NN.png (every candidate kept); the picks below are the art-directed
choices. All sources were generated on the game's own palette (tools/pixellab/pilot.py passes each asset's palette
families to PixelLab), so every pixel maps exactly back onto a palette index: night, season and weather tables keep
working (an oak canopy is still the 'oak' ramp and still turns in autumn).

Picks replace library sprites by name (so placement rules, collision, depth and tests keep working) or add new names.
The replaced sprites' older art stays in the code; nothing on disk is overwritten until the build exports.
"""
from __future__ import annotations
import os, json
import numpy as np
from PIL import Image
from .canvas import Canvas
from .palette import PAL

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'assets/pixellab/src')
DB = os.path.join(ROOT, 'assets/pixellab/pilot.json')


def _families(asset):
    try: return json.load(open(DB))[asset]['palette_families']
    except Exception: return None


def to_palette(rgba, fams):
    """Exact colour -> palette index, searching only this asset's families (several families share colours, e.g.
    oak and oak_b); anything unexpected falls to the nearest colour among the same families."""
    idxs = [PAL.index[(f, r)] for f in fams for r in range(len(PAL.ramp(f)))]
    cols = np.array([PAL.day[i][:3] for i in idxs], dtype=float)
    rgb = rgba[:, :, :3].astype(float); a = rgba[:, :, 3]
    d = ((rgb[:, :, None, :] - cols[None, None]) ** 2).sum(3)
    c = Canvas(rgba.shape[1], rgba.shape[0]); c.a = np.array(idxs, dtype=np.uint8)[d.argmin(2)]; c.a[a < 128] = 0
    return c, float(np.sqrt(d.min(2)[a >= 128]).max()) if (a >= 128).any() else 0.0


def despeckle(c, passes=2):
    """Quiet the art without changing its shapes: a pixel unlike all four of its neighbours (a lone speck) takes the
    colour most of its eight neighbours share. Outlines and clusters of two or more pixels are left alone."""
    a = c.a.copy(); h, w = a.shape
    for _ in range(passes):
        p = np.pad(a, 1)
        n4 = np.stack([p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]])
        lone = (a != 0) & np.all(n4 != a[None], axis=0) & np.all(n4 != 0, axis=0)
        ys, xs = np.nonzero(lone)
        out = a.copy()
        for y, x in zip(ys, xs):
            nb = p[y:y + 3, x:x + 3].ravel(); nb = nb[(nb != 0)]
            vals, cnt = np.unique(nb, return_counts=True); out[y, x] = vals[cnt.argmax()]
        a = out
    r = c.copy(); r.a = a; return r


def load(asset, k):
    p = os.path.join(SRC, asset, f'cand_{k:02d}.png')
    a = np.array(Image.open(p).convert('RGBA'))
    ys, xs = np.nonzero(a[:, :, 3] >= 128)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    pad = np.zeros((a.shape[0] + 2, a.shape[1] + 4, 4), np.uint8); pad[1:-1, 2:-2] = a       # a little room for outlines and snow caps
    return pad


def _origin(c, fams_base=None):
    """Ground contact: the bottom row of solid pixels; x is the balance point of the lowest quarter of the sprite
    (for trees, of the trunk's wood pixels near the ground), so pegs, ropes and stray tufts do not pull it aside."""
    m = c.a != 0
    rows = np.nonzero(m.any(1))[0]; bot, top = rows.max(), rows.min()
    y0 = int(bot - max(3, (bot - top) * 0.25))
    sel = m[y0:bot + 1]
    if fams_base:
        wood = np.isin(c.a[max(0, bot - 6):bot + 1], [PAL.index[(f, r)] for f in fams_base for r in range(len(PAL.ramp(f)))])
        if wood.any(): sel = wood
    xs = np.nonzero(sel)[1]
    return int(round(np.median(xs))), int(bot)


# name: (asset, candidate, kind) ; kind sets tags, shadow and contact like the sprites they replace
PICKS = {
    'oak_0': ('oak', 6, 'tree'), 'oak_1': ('oak', 1, 'tree'), 'oak_2': ('oak', 8, 'tree'), 'oak_3': ('oak', 5, 'tree'),
    'pine_0': ('pine', 0, 'tree'), 'pine_1': ('pine', 3, 'tree'), 'pine_new0': ('pine', 6, 'tree'), 'pine_new1': ('pine', 11, 'tree'),
    'rock_xl': ('rocks', 2, 'rock'), 'rock_l0': ('rocks', 12, 'rock'), 'rock_l1': ('rocks', 17, 'rock'), 'rock_m0': ('rocks_small', 13, 'rock'),
    'rock_m1': ('rocks_small', 28, 'rock'), 'rock_s0': ('rocks_small', 18, 'rock'), 'rock_s1': ('rocks_small', 43, 'rock'), 'rock_s2': ('rocks_small', 58, 'rock'),
    'shrooms_brown': ('mushrooms_s', 15, 'plant'), 'shrooms_red': ('mushrooms_s', 11, 'plant'), 'shrooms_tan': ('mushrooms_s', 57, 'plant'),
    'patch_daisy': ('flowers_s', 0, 'flower'), 'patch_daisy_s': ('flowers_s', 32, 'flower'), 'patch_blue': ('flowers_s', 43, 'flower'),
    'patch_butter': ('flowers_s', 3, 'flower'), 'patch_pink': ('flowers_s', 17, 'flower'), 'patch_bells': ('flowers_s', 25, 'flower'),
    'flowerbush_daisy': ('flowers', 38, 'flower'), 'flowerbush_bells': ('flowers', 44, 'flower'), 'flowerbush_butter': ('flowers', 51, 'flower'),
    'bush_a': ('bush', 0, 'bush'), 'bush_b': ('bush', 15, 'bush'), 'bush_berry': ('bush', 11, 'bush'), 'bush_c': ('bush', 20, 'bush'),
    'hollowlog_0': ('log', 15, 'log'), 'log_moss': ('log', 0, 'log'), 'log_cut': ('log', 8, 'log'),
    # flat 2D, front-facing (the user: keep everything 2D) - the corner-angle tent, crate, bench and woodpile were regenerated
    'tent': ('tent2d', 0, 'tent'), 'campfire': ('campfire', 10, 'fire'), 'lantern_post': ('lantern', 21, 'lantern'), 'woodpile': ('woodpile2d', 0, 'prop'),
    'chop_block': ('chopblock', 13, 'prop'), 'supply_crate': ('crate2d', 36, 'prop'), 'log_seat': ('bench2d', 9, 'prop'), 'log_seat_b': ('bench2d', 31, 'prop'),
    'fern_a': ('fern', 5, 'plant'), 'fern_b': ('fern', 12, 'plant'), 'fern_c': ('fern', 22, 'plant'),
    'tall_a': ('tallgrass', 0, 'plant'), 'tall_b': ('tallgrass', 8, 'plant'), 'tall_c': ('tallgrass', 15, 'plant'),
    'gd_tuft_0': ('gd_tufts', 3, 'detail'), 'gd_tuft_1': ('gd_tufts', 16, 'detail'), 'gd_clover_0': ('gd_clover', 4, 'detail'), 'gd_clover_1': ('gd_clover', 13, 'detail'),
    'gd_specks_0': ('gd_specks', 5, 'detail'), 'gd_specks_1': ('gd_specks', 14, 'detail'), 'gd_specks_2': ('gd_specks', 23, 'detail'),
    'gd_pebbles_0': ('gd_pebbles', 5, 'detail'), 'gd_pebbles_1': ('gd_pebbles', 18, 'detail'), 'gd_pebbles_2': ('gd_pebbles', 12, 'detail'),
    'gd_litter_0': ('gd_litter', 8, 'detail'), 'gd_litter_1': ('gd_litter', 19, 'detail'),
    'tuft_0': ('tuft', 3, 'plant'), 'tuft_1': ('tuft', 11, 'plant'), 'tuft_2': ('tuft', 23, 'plant'),
}


def sprite_for(name, asset, k, kind, prev=None):
    from .objects import Sprite
    fams = _families(asset)
    c, err = to_palette(load(asset, k), fams)
    c = despeckle(c)                                                      # lone specks out: the user found the art too noisy
    base = {'tree': ['wood'], 'log': None, 'rock': None}.get(kind)
    ox, oy = _origin(c, base)
    w = c.w
    if kind not in ('tree', 'lantern'): ox = w // 2                    # props and plants stand on their middle
    if kind == 'tree':
        return Sprite(name, c, ox, oy + 1, shadow=(max(9, int(w * 0.38)), 4, 6, -1), soft_shadow=True, tags=('tree', 'ysort'), contact=(5, 1.6))
    if kind == 'rock':
        return Sprite(name, c, ox, oy + 1, shadow=(int(w * 0.45), max(2, int(c.h * 0.12)), 2, 0), soft_shadow=True, tags=('rock', 'ysort', 'solid'), contact=(w * 0.4, 1.4), ground_blend=True)
    if kind == 'bush':
        return Sprite(name, c, ox, oy + 1, shadow=(int(w * 0.45), 3, 2, 0), soft_shadow=True, tags=('plant', 'ysort', 'shrub', 'solid'), contact=(w * 0.38, 1.4))
    if kind == 'log':
        return Sprite(name, c, ox, oy + 1, shadow=(int(w * 0.45), 3, 2, 0), soft_shadow=True, tags=('prop', 'ysort', 'solid'), contact=(w * 0.4, 1.6), ground_blend=True)
    if kind == 'tent':
        return Sprite(name, c, ox, oy + 1, shadow=(int(w * 0.46), 5, 6, -1), soft_shadow=True, tags=('structure', 'ysort'), contact=(w * 0.38, 2.0))
    if kind == 'fire':
        return Sprite(name, c, ox, oy - 2, shadow=None, tags=('prop', 'ysort', 'light', 'solid'), contact=(w * 0.38, 2.0), ground_blend=True)
    if kind == 'lantern':
        return Sprite(name, c, ox, oy + 1, shadow=(5, 2, 3, 0), soft_shadow=True, tags=('structure', 'ysort', 'light', 'solid'), contact=(4, 1.2))
    if kind == 'prop':
        return Sprite(name, c, ox, oy + 1, shadow=(int(w * 0.42), 3, 2, 0), soft_shadow=True, tags=('prop', 'ysort', 'solid'), contact=(w * 0.38, 1.5), ground_blend=True)
    if kind == 'detail':
        return Sprite(name, c, ox, oy, shadow=None, tags=('ground',))
    if kind == 'flower':
        return Sprite(name, c, ox, oy + 1, shadow=None, tags=('plant', 'ysort', 'flower'))
    return Sprite(name, c, ox, oy + 1, shadow=None, tags=('plant', 'ysort', 'mushroom'))


def add_pilot(lib, picks=None):
    """Swap the picked PixelLab art into the library; returns {name: worst colour error} for the report."""
    import dataclasses
    report = {}
    for name, (asset, k, kind) in (picks or PICKS).items():
        if not os.path.exists(os.path.join(SRC, asset, f'cand_{k:02d}.png')): continue
        s = sprite_for(name, asset, k, kind, lib.get(name))
        lib[name] = s
        if kind == 'fire':                                                    # the same ring, with the fire banked to embers, and cold
            for state, nm in (('embers', 'campfire_embers'), ('unlit', 'campfire_unlit')):
                c = s.c.copy(); F = PAL.ramp('fire'); E = PAL.ramp('ember')
                fm = np.isin(c.a, F); rows = np.nonzero(fm.any(1))[0]
                if len(rows):
                    low = np.zeros_like(fm); cut = int(rows.max() - (rows.max() - rows.min()) * 0.25); low[cut:] = True
                    c.a[fm & ~low] = 0
                    c.a[fm & low] = (F[0] if state == 'embers' else E[0])
                lib[nm] = dataclasses.replace(s, name=nm, c=c)
    return report
