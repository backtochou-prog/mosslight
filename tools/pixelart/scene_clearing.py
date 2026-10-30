"""THE FIRST SCENE: a forest clearing with a survival tent.

Landmarks are placed by hand. The forest, understorey, pond margin, path
decoration, sheltered corners and ruin overgrowth come from the composition
rules in composition.py with a fixed seed, so the scene is reproducible and
the same rules can build other clearings in this biome.
"""
from __future__ import annotations
import math, random
import numpy as np
from .canvas import Canvas
from .palette import PAL
from .terrain_tiles import T, GRASS, WORN, FOREST, SAND, DIRT, EARTH, PEBBLE, MUD, STONE, MOSSY, PAVED, SHALLOW, WATER
from .render import Scene, Light
from .paths import Path
from . import composition as C

W_T, H_T = 48, 30

def px(t): return int(round(t * T))

CLEARING = ((19.5, 15.5, 13.5, 9.5), (38, 16, 8.5, 6.8), (26, 23, 7, 4.5), (31, 11, 5, 3.5))
def clearing_dist(x, y):
    best = 1e9
    for (cx, cy, rx, ry) in CLEARING:
        d = math.hypot((x - cx) / rx, (y - cy) / ry) - 1.0
        best = min(best, d * min(rx, ry))
    return best

def build(lib) -> Scene:
    sc = Scene(W_T, H_T)
    sc.lib = lib
    mm = sc.mm
    mm.set_lush(seed=21)

    # ------------------------------------------------------------------ terrain
    mm.m[:, :] = FOREST
    mm.metaball([(17, 14, 7.5), (23, 13, 6.5), (28, 16, 5.5), (12, 20, 5), (20, 21, 5), (34, 14, 5.5), (39, 16, 6),
                 (35, 20, 4), (31, 10, 3.5), (26, 24, 3.5), (31, 16, 4.2), (31, 20, 3.6)], GRASS, threshold=0.8, mode='set')
    for _ in range(2):                                    # no forest slivers between carve shapes
        f = mm.m == FOREST; p = np.pad(f, 1)
        nb = sum(p[1 + dy:p.shape[0] - 1 + dy, 1 + dx:p.shape[1] - 1 + dx].astype(int) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dx, dy) != (0, 0))
        mm.m[f & (nb <= 3)] = GRASS
    mm.metaball([(12, 10, 2.5)], FOREST)
    mm.disc(17.5, 16.3, 2.6, WORN); mm.disc(19.6, 17, 1.9, WORN)
    # paths: the main way to the dock (widening at the camp), the narrow climb to the ruin
    main = Path([(4.5, 30.5), (6.5, 27), (9.5, 24), (13.5, 21.5), (17.5, 19.5), (22, 18.6), (26.5, 19.2), (30, 18.4), (33, 17.2)],
                width=[0.85, 0.9, 0.95, 1.0, 1.1, 1.0, 0.95, 0.9, 0.85], surface=DIRT, verge=WORN, verge_width=1.4, seed=3)
    branch = Path([(27.5, 19), (29.5, 15.5), (31.5, 12), (34, 9.3), (36.5, 7.6)], width=0.7, surface=DIRT, verge=WORN, verge_width=1.05, seed=8)
    main.stamp(mm); branch.stamp(mm)
    Path.aprons(mm, [main, branch])
    mm.metaball([(31.6, 17.6, 1.0), (33.0, 17.3, 1.0)], PEBBLE)       # pebbled landing at the dock
    # pond: shallow rim, deep heart, a small sandy bank on the south-west
    mm.pond([(38.5, 15.5, 3.4), (41, 17.5, 2.8), (37.5, 18.5, 2.4), (40.5, 14.2, 2.0)], deep_threshold=2.1, shore=False)
    mm.metaball([(37.6, 21.3, 1.3)], SAND)
    # ruin floor: flagstones with earth between
    mm.metaball([(37.5, 6.3, 2.2), (39.2, 6.5, 1.6)], DIRT)
    mm.metaball([(37.8, 6.2, 1.7), (39.0, 6.4, 1.2)], PAVED)
    # leaf litter builds up under the big trees at the edge
    for (x, y, r) in ((13, 13, 3), (7.5, 9.5, 3), (27, 7.5, 3), (20.5, 26, 3), (38.5, 19, 2), (6, 21, 2.5)):
        mm.litter_disc(x, y, r, 0.9)

    ctx = C.Context(sc, lib, seed=2026, paths=[main, branch],
                    keepouts=[(272, 250, 44), (318, 270, 26), (560, 290, 40), (616, 100, 60), (418, 190, 16)])

    # ------------------------------------------------------------------ landmarks (hand-placed)
    for (nm, x, y, fl) in (('tent', 272, 244, False), ('campfire', 318, 270, False), ('log_seat', 296, 294, False), ('lantern_post', 236, 262, False),
                           ('stump_0', 352, 306, False), ('oak_0', 216, 206, False), ('boulder_l0', 318, 214, False), ('boulder_mossy_m1', 352, 226, False),
                           ('boulder_s0', 300, 230, False), ('dock', 540, 282, False), ('ruin_back', 616, 94, False), ('ruin_side', 560, 130, False),
                           ('rubble_0', 672, 108, False), ('rubble_1', 548, 142, False), ('beam', 606, 126, False), ('rowan_1', 640, 118, False),
                           ('dead_0', 700, 150, False), ('hollowlog_0', 480, 400, False), ('rowan_0', 418, 186, False), ('willow_0', 690, 232, True),
                           ('boulder_mossy_l0', 610, 338, False), ('boulder_s1', 640, 346, False)):
        ctx.place(nm, x, y, flip=fl)
    sc.add(lib['lantern_hanging'], 583, 262); sc.add(lib['lantern_hanging'], 612, 88)
    sc.add(lib['glowshroom_0'], 596, 132); sc.add(lib['glowshroom_1'], 684, 122); sc.add(lib['glowshroom_0'], 500, 408)
    sc.add(lib['fern_1'], 288, 236); sc.add(lib['fern_0'], 372, 236, flip=True); sc.add(lib['fern_2'], 512, 388)
    sc.add(lib['shroom_1'], 456, 414); sc.add(lib['branch_0'], 150, 330); sc.add(lib['branch_1'], 420, 150, flip=True)
    sc.add(lib['flowers_b1'], 440, 198); sc.add(lib['stone_0'], 400, 196)

    # ------------------------------------------------------------------ rules
    def species(band, tx, ty, r_):
        ang = math.atan2(ty - 15.5, tx - 24); north = -2.6 < ang < -0.5
        if band == 0: return r_.choice(['oak_0', 'oak_1', 'oak_2', 'oak_3', 'birch_0', 'birch_1', 'rowan_0'] if not north else ['oak_1', 'oak_3', 'pine_0', 'birch_0'])
        return r_.choice(['pine_0', 'pine_1', 'oak_0', 'oak_2', 'oak_3'] if north else ['oak_0', 'oak_1', 'birch_1', 'pine_1', 'oak_2'])
    def exclude(tx, ty):
        if ty < 4.4: return True
        if 33 < tx < 44 and 2.5 < ty < 9.5: return True
        if abs(tx - (29.5 + (ty - 15.5) * -0.75)) < 1.3 and 7.5 < ty < 16: return True
        return False
    C.forest_edge(ctx, clearing_dist, species, exclude=exclude)
    C.understorey(ctx, clearing_dist)
    C.pond_margin(ctx, keep=lambda x, y: not (500 < x < 600 and 250 < y < 310))
    trees = [(p.x, p.y) for p in sc.placements if 'tree' in p.sprite.tags and 'sapling' not in p.sprite.tags]
    C.path_decorate(ctx, trees)
    C.sheltered_corner(ctx, 190, 232)              # under the big oak, beside the tent
    C.sheltered_corner(ctx, 112, 300)
    C.ruin_overgrowth(ctx, 556, 90, 680, 136)
    # sunny meadow: wildflowers in two loose drifts, none in the shade
    C.vegetation_cluster(ctx, 400, 350, 70, [('flowers_w', 2, 3), ('flowers_b', 2, 2), ('flowers_y', 2, 1), ('tuft_', 3, 2)], spacing=16, n=9)
    C.vegetation_cluster(ctx, 560, 380, 50, [('flowers_p', 2, 2), ('flowers_r', 2, 1), ('tallgrass_', 3, 2), ('tuft_', 3, 1)], spacing=16, n=6)
    C.vegetation_cluster(ctx, 170, 262, 36, [('flowers_w', 2, 2), ('shroom_', 2, 1), ('tuft_', 3, 1)], spacing=14, n=4)
    C.foreground_frame(ctx)
    for (x, y, rx, ry) in ((176, 192, 11, 6), (300, 190, 8, 4), (150, 110, 9, 5), (660, 380, 10, 6)):
        sc.decals.append(C.moss_patch(x, y, rx, ry))
    sc.decals.append(C.pebbles(520, 280, 22, 7)); sc.decals.append(C.pebbles(330, 318, 18, 5))
    sc.decals.append(distant_backdrop)

    # ------------------------------------------------------------------ night-only
    ff = PAL.i('firefly', 0)
    for (x, y) in ((300, 330), (340, 300), (380, 340), (420, 290), (250, 300), (460, 360), (530, 330), (590, 250), (620, 290), (660, 320), (560, 300), (200, 350), (350, 400), (500, 250), (440, 390), (610, 230)):
        sc.night_pixels.append((x, y, ff)); sc.night_pixels.append((x + 1, y, ff))
        sc.lights.append(Light(x, y, 7, color=(0.75, 0.95, 0.55), intensity=0.55))
    eyes = PAL.i('eyes', 0)
    for (x, y) in ((118, 206), (121, 206)): sc.night_pixels.append((x, y, eyes))
    ml = PAL.ramp('moonlight')
    for (x, y, L) in ((632, 250, 3), (640, 256, 4), (628, 262, 3), (644, 268, 5), (636, 274, 3), (648, 280, 4), (640, 288, 3), (652, 294, 2)):
        for i in range(L): sc.night_pixels.append((x + i, y, ml[2] if 0 < i < L - 1 else ml[1]))
    # ------------------------------------------------------------------ lights
    sc.lights.append(Light(244, 271, 62, color=(1.0, 0.84, 0.58)))
    sc.lights.append(Light(318, 262, 50, color=(1.0, 0.72, 0.42), intensity=0.95))
    sc.lights.append(Light(272, 236, 34, color=(1.0, 0.80, 0.55), intensity=0.6))
    sc.lights.append(Light(583, 256, 52, color=(1.0, 0.84, 0.58)))
    sc.lights.append(Light(612, 82, 48, color=(1.0, 0.84, 0.58), intensity=0.9))
    for (x, y) in ((596, 134), (684, 124), (500, 410)): sc.lights.append(Light(x, y, 14, color=(0.55, 0.95, 1.0), intensity=0.5))
    sc.playable = (32, 48, sc.W - 64, sc.H - 80)
    sc.paths = [main, branch]
    return sc


def distant_backdrop(c: Canvas, rng):
    far = PAL.ramp('haze_far'); near = PAL.ramp('haze_near'); mist = PAL.ramp('mist')
    W = c.w
    c.rect(0, 0, W, 46, far[1])
    r = random.Random(5)
    for x in range(-20, W + 20, 26):
        rad = r.randint(14, 20); yb = 30 + r.randint(-4, 4)
        c.ellipse(x, yb, rad, rad * 0.8, far[0]); c.ellipse(x - 3, yb - 3, rad * 0.6, rad * 0.5, far[2])
    tx = 584
    c.rect(tx - 10, 6, 20, 12, far[0]); c.ellipse(tx, 6, 10, 3, far[2]); c.rect(tx - 7, 18, 2, 16, far[0]); c.rect(tx + 5, 18, 2, 16, far[0]); c.line(tx - 6, 22, tx + 6, 32, far[0])
    for x in range(-10, W + 20, 24):
        rad = r.randint(16, 22); yb = 58 + r.randint(-4, 4)
        c.ellipse(x, yb, rad, rad * 0.75, near[1]); c.ellipse(x - 3, yb - 4, rad * 0.55, rad * 0.45, near[2]); c.ellipse(x + 4, yb + 5, rad * 0.7, rad * 0.4, near[0])
    bayer = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
    for y in range(0, 56):
        dens = max(0.0, 1.0 - y / 56) ** 2.0 * 0.55
        if dens < 0.2: break
        for x in range(W):
            if bayer[y % 4][x % 4] / 16 < dens:
                c.put(x, y, mist[1] if y > 12 else mist[2])
