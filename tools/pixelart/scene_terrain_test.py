"""TERRAIN TEST SCENE: deliberately difficult material combinations.

Winding path with two junctions and a width change, a pebbled branch, a
packed-earth branch ending on abandoned paving, a pond with irregular banks
(shallow + deep, sand on the south bank), a natural-stone outcrop with mossy
stone, dense forest edge with small clearings, and a snow patch in the
north-east corner. Rendered in spring (with the snow patch) and as a full
winter test.
"""
from __future__ import annotations
import random
import numpy as np
from .terrain_tiles import (T, GRASS, WORN, FOREST, SAND, DIRT, EARTH, PEBBLE, MUD, STONE, MOSSY, PAVED, SHALLOW, WATER)
from .render import Scene

W_T, H_T = 40, 26

def build(lib) -> Scene:
    from .paths import Path
    sc = Scene(W_T, H_T)
    mm = sc.mm
    mm.set_lush(seed=5)
    mm.metaball([(4, 4, 6), (12, 3, 6), (20, 2, 5), (3, 12, 5), (9, 9, 4)], FOREST)
    mm.metaball([(8, 7, 2.2)], GRASS, mode='set')
    mm.metaball([(16, 5, 1.8)], GRASS, mode='set')
    # paths
    main = Path([(1, 24), (5, 21), (9, 20.5), (13, 17.5), (18, 16), (23, 16.5), (28, 15), (33, 12), (38, 11)],
                width=[0.8, 0.9, 1.0, 1.2, 1.2, 1.0, 0.9, 0.8, 0.8], surface=DIRT, verge=WORN, verge_width=1.35, seed=3)
    pebbled = Path([(13, 17.5), (12, 13), (14, 9), (17, 6.5)], width=0.7, surface=PEBBLE, verge=WORN, verge_width=1.05, seed=8)
    packed = Path([(23, 16.5), (26, 20), (30, 22.5)], width=0.8, surface=EARTH, verge=WORN, verge_width=1.1, seed=12)
    for p in (main, pebbled, packed): p.stamp(mm)
    Path.aprons(mm, [main, pebbled, packed])
    # abandoned paving at the end of the packed branch, grass creeping in
    mm.metaball([(31.5, 23.5, 2.0), (33, 22.8, 1.4)], DIRT)
    mm.metaball([(31.6, 23.4, 1.6), (33, 22.8, 1.1)], PAVED)
    # pond with irregular banks: shallow rim, deep core, sand on the south bank
    mm.pond([(31, 6.5, 2.6), (34.5, 7.5, 2.4), (32, 9.5, 2.0), (29, 8.5, 1.5)], deep_threshold=2.0)
    mm.metaball([(31, 11.6, 1.6), (33.5, 11.2, 1.2)], SAND)
    # natural stone outcrop in the forest with a mossy section; a lone slab in grass
    mm.metaball([(6, 15, 2.2), (8.5, 16, 1.8)], STONE)
    mm.metaball([(6, 15.8, 1.3)], MOSSY)
    mm.metaball([(21, 22.5, 1.3)], STONE)
    # mud hollow in the forest
    mm.metaball([(4, 9, 1.4)], MUD)
    # leaf litter under the forest edge
    for (x, y, r) in ((10, 8, 4), (18, 4, 3), (4, 14, 3)): mm.litter_disc(x, y, r, 0.8)
    # snow patch in the north-east corner, covering grass, path and stone
    sc.mm.metaball([(37, 2, 2.2)], STONE)
    sc.mm.snow_region([(37, 3, 3.6), (33, 2, 2.4), (38.5, 7, 1.6)])
    if lib is None: return sc
    # ---- vegetation by rules (same rules as the clearing)
    from . import composition as C
    sc.lib = lib
    ctx = C.Context(sc, lib, seed=7, paths=[main, pebbled, packed])
    def forest_dist(tx, ty):      # <0 inside the forest ground region (we want trees *in* the forest here)
        return -1.0 if mm.m[min(mm.h, int(ty)), min(mm.w, int(tx))] == FOREST else 1.0
    def species(band, tx, ty, r_):
        return r_.choice(['oak_0', 'oak_1', 'oak_2', 'oak_3', 'pine_0', 'pine_1', 'birch_0'])
    # dense forest = trees where the ground is forest floor
    C.forest_edge(ctx, lambda tx, ty: 1.5 if forest_dist(tx, ty) < 0 else -1.0, species, spacing=(2.3, 2.3, 2.3), min_edge=0.9,
                  exclude=lambda tx, ty: mm.snow[min(mm.h, int(ty)), min(mm.w, int(tx))] > 0)
    C.pond_margin(ctx)
    trees = [(p.x, p.y) for p in sc.placements if 'tree' in p.sprite.tags]
    C.path_decorate(ctx, trees)
    ctx.place('willow_1', 445, 190, flip=True)
    ctx.place('boulder_mossy_l1', 118, 262); ctx.place('boulder_mossy_m0', 140, 274); ctx.place('boulder_m1', 352, 362)
    C.sheltered_corner(ctx, 150, 290)
    ctx.place('hedge_0', 300, 330); ctx.place('hedge_1', 240, 60)
    C.vegetation_cluster(ctx, 560, 330, 60, [('flowers_w', 2, 2), ('flowers_r', 2, 1), ('flowers_y', 2, 1), ('tallgrass_', 3, 2), ('tuft_', 3, 2)], spacing=16, n=9)
    C.vegetation_cluster(ctx, 420, 110, 40, [('fern_', 3, 2), ('tallgrass_', 3, 1), ('sapling_birch', 2, 1)], spacing=14, n=5)
    for (nm, x, y) in (('pine_0', 592, 40), ('pine_1', 560, 70), ('boulder_l1', 612, 118), ('shrub_2', 540, 40), ('stump_0', 468, 60)):
        ctx.place(nm, x, y)
    return sc
