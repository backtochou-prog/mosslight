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
from . import ground_art as GA

W_T, H_T = 48, 30

def px(t): return int(round(t * T))

CLEARING = ((19.5, 15.5, 13.5, 9.5), (38, 16, 8.5, 6.8), (26, 23, 7, 4.5), (31, 11, 5, 3.5), (43, 26, 5.5, 5.5))
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
    # paths: the main way to the dock (widening at the camp), the narrow climb to the ruin
    main = Path([(4.5, 30.5), (6.5, 27), (9.5, 24), (13.5, 21.5), (17.5, 19.5), (22, 18.6), (26.5, 19.2), (30, 18.4), (33, 17.2)],
                width=[0.75, 0.78, 0.8, 0.85, 0.9, 0.85, 0.8, 0.78, 0.75], surface=DIRT, verge=WORN, verge_width=0.95, seed=3)
    branch = Path([(27.5, 19), (29.5, 15.5), (31.5, 12), (34, 9.3), (36.5, 7.6)], width=0.7, surface=DIRT, verge=WORN, verge_width=1.05, seed=8)
    east = Path([(34, 21), (36.5, 23.2), (38, 24), (44.6, 24.1), (47.5, 25)], width=0.6, surface=DIRT, verge=WORN, verge_width=0.7, seed=11)
    main.stamp(mm); branch.stamp(mm); east.stamp(mm)
    Path.aprons(mm, [main, branch])
    mm.metaball([(31.6, 17.6, 1.0), (33.0, 17.3, 1.0)], PEBBLE)       # pebbled landing at the dock
    # pond: shallow rim, deep heart, a small sandy bank on the south-west
    mm.pond([(38.5, 15.5, 3.4), (41, 17.5, 2.8), (37.5, 18.5, 2.4), (40.5, 14.2, 2.0)], deep_threshold=2.1, shore=False)
    mm.metaball([(37.6, 21.3, 1.3)], SAND)
    # the river: comes in from the east past the ruin's foot, feeds the pond, leaves south under the footbridge
    RIVER_IN = [(50, 7.5, 2.3), (48, 9, 2.3), (46.5, 11.4, 2.2), (45, 12.4, 2.2), (43.6, 13, 2.2)]
    RIVER_OUT = [(39.8, 21, 2), (40.4, 22.8, 1.9), (40.9, 24.6, 1.9), (42.4, 26.2, 1.95), (43.6, 28, 2), (42.6, 30.5, 2.1)]
    mm.pond(RIVER_IN, deep_threshold=1.75, shore=False); mm.pond(RIVER_OUT, deep_threshold=1.75, shore=False)
    # ruin floor: flagstones with earth between
    mm.metaball([(37.5, 6.3, 2.2), (39.2, 6.5, 1.6)], DIRT)
    mm.metaball([(37.8, 6.2, 1.7), (39.0, 6.4, 1.2)], PAVED)
    # leaf litter builds up under the big trees at the edge
    for (x, y, r) in ((13, 13, 3), (7.5, 9.5, 3), (27, 7.5, 3), (20.5, 26, 3), (38.5, 19, 2), (6, 21, 2.5)):
        mm.litter_disc(x, y, r, 0.9)
    # THE STONY RISE (north-west): the valley's bones come to the surface; bare rock shelves, a mossy step, thin soil
    # THE SEDGE MARSH (south-east, where the river spreads out below the bridge): mud flats, standing pools
    mm.metaball([(37.6, 27.4, 2.6), (39.6, 29.4, 2.2), (46.0, 26.8, 2.4), (46.8, 29.6, 2.2), (44.2, 25.2, 1.4)], MUD, threshold=0.85)
    mm.pond([(37.4, 28.2, 1.25), (46.4, 27.6, 1.15), (39.2, 30.0, 1.0)], deep_threshold=9, shore=False)

    ctx = C.Context(sc, lib, seed=2026, paths=[main, branch],
                    keepouts=[(272, 250, 48), (318, 276, 34), (560, 290, 40), (616, 100, 60), (418, 190, 18), (330, 224, 40), (470, 358, 44), (654, 380, 70)])

    # ------------------------------------------------------------------ landmarks, composed as clusters
    def put(nm, x, y, fl=False):            # hand-placed: always placed where the artist put it, and it reserves its ground
        sc.add(lib[nm], int(x), int(y), flip=fl); ctx.reserve(x, y, C.footprint_radius(lib[nm]))
    # THE CAMP — a refuge someone lives in: the tent backs onto the big oak and the rock
    # outcrop (shelter from the north), its mouth faces the fire; the fire pit sits on a
    # worn patch between tent and path; firewood is stacked by the tent where it stays dry;
    # the lantern post stands where it lights both the entrance and the fire; a flat stone
    # is the step at the tent mouth; two seats face the fire.
    for (nm, x, y, fl) in (('oak_0', 216, 206, False), ('tent', 248, 246, False), ('woodpile', 182, 240, False), ('chop_block', 192, 268, False),
                           ('lantern_post', 232, 270, False), ('supply_crate', 284, 262, False), ('forage_basket', 270, 266, False), ('water_bucket', 340, 270, False),
                           ('campfire', 318, 274, False), ('log_seat', 302, 300, False), ('log_seat_b', 352, 286, True)):
        put(nm, x, y, fl)
    # THE OUTCROP — a broken shelf of the same stone behind the tent: one big block, a mossy second leaning on it,
    # small pieces that have split off at its foot. Ferns grow in its shade. Small stones gather by big ones.
    for (nm, x, y, fl) in (('rock_xl', 324, 216, False), ('rock_m1', 347, 222, False), ('rock_m0', 304, 222, True), ('rock_s1', 336, 228, False),
                           ('rock_s0', 360, 228, False), ('rock_s2', 314, 229, False), ('fern_1', 292, 232, False), ('fern_0', 372, 234, True), ('tuft_2', 312, 230, False)):
        put(nm, x, y, fl)
    # CAMP DRESSING — plants where plants would be: ferns and long grass in the shade and shelter of things (the oak's
    # foot, the lee of the rocks, the tent's back corners, the ends of the seat logs), flowers in the sun at the
    # camp's edge where nobody walks, mushrooms in the damp under the oak.
    for (nm, x, y, fl) in (('fern_b', 200, 214, False), ('shrooms_brown', 234, 212, False), ('tall_b', 164, 246, True), ('tall_a', 212, 254, False),
                           ('fern_c', 302, 242, True), ('tall_b', 308, 232, False), ('patch_daisy_s', 366, 240, False), ('tall_c', 381, 232, False),
                           ('patch_blue', 212, 262, False), ('tall_c', 336, 314, True), ('patch_butter', 270, 308, False), ('tall_a', 384, 280, False),
                           ('patch_daisy', 236, 300, True), ('tall_b', 168, 276, False), ('fern_a', 160, 230, False)):
        put(nm, x, y, fl)
    # THE STONY RISE — rock shelves stepping up toward the north-west woods, dark firs on the thin soil, heather in
    # the cracks, scree fallen to the foot of each shelf. A different place from the meadow a few steps away.
    for (nm, x, y, fl) in (('pine_0', 44, 118, False), ('ledge_2', 82, 112, False), ('pine_1', 128, 92, True), ('ledge_0', 150, 120, True),
                           ('ledge_1', 58, 146, False), ('pine_0', 178, 112, False), ('pine_1', 26, 150, True), ('heather_0', 104, 126, False),
                           ('heather_1', 124, 132, False), ('heather_0', 74, 156, True), ('rock_s0', 116, 116, False), ('rock_s2', 168, 128, False),
                           ('rock_m0', 36, 160, False), ('heather_1', 160, 140, True), ('rock_s1', 92, 160, False), ('tuft_2', 140, 138, False)):
        put(nm, x, y, fl)
    # THE SEDGE MARSH — where the river slows and spreads below the bridge: sedge tussocks, cattails at the pool
    # edges, lily pads on the still water, a willow leaning over it, a drowned tree gone silver.
    for (nm, x, y, fl) in (('willow_1', 618, 446, False), ('dead_0', 708, 430, True), ('sedge_0', 586, 436, False), ('sedge_1', 628, 432, True),
                           ('cattail_tall', 606, 458, False), ('sedge_0', 730, 432, True), ('cattail_tall', 736, 458, True), ('sedge_1', 756, 448, False),
                           ('marsh_grass', 662, 428, False), ('reeds_1', 584, 462, False), ('marsh_grass', 690, 452, True), ('sedge_1', 650, 464, False)):
        put(nm, x, y, fl)
    for (nm, x, y) in (('lily_0', 598, 452), ('lily_2', 608, 446), ('lily_3', 744, 444), ('lily_1', 736, 440), ('lily_2', 626, 478)):
        sc.add(lib[nm], x, y, layer='ground')
    # WAYMARKS — a sign where the ruin path leaves the main path; a split-rail fence keeping the east path off the soft marsh edge
    for (nm, x, y, fl) in (('signpost', 474, 232, False), ('fence_3', 574, 406, False), ('fence_2', 622, 410, True)):
        put(nm, x, y, fl)
    # THE POND — dock on the near bank at the path's end, willow on the far bank, a mossy
    # boulder pair where the bank turns, reeds and lilies by rule.
    for (nm, x, y, fl) in (('willow_0', 730, 306, True), ('rock_xl', 600, 338, True), ('rock_s0', 577, 347, False), ('rock_s1', 584, 352, False)):
        put(nm, x, y, fl)
    sc.add(lib['dock'], 528, 290, layer='ground'); sc.add(lib['lantern_hanging'], 592, 268)
    if 'ruin_wall' in lib: sc.add(lib['ruin_wall'], 512, 104)
    if 'bridge' in lib: sc.add(lib['bridge'], 654, 390, layer='ground')
    # THE RUIN — two walls, rubble at the ends, a fallen beam, a young rowan growing inside,
    # a dead tree beyond, glow-caps in the damp corner.
    for (nm, x, y, fl) in (('ruin_back', 616, 94, False), ('ruin_side', 560, 130, False), ('rubble_0', 672, 108, False), ('rubble_1', 548, 142, False),
                           ('beam', 606, 126, False), ('rowan_1', 640, 118, False), ('dead_0', 700, 150, False)):
        put(nm, x, y, fl)
    sc.add(lib['lantern_hanging'], 612, 88); sc.add(lib['glowshroom_0'], 596, 132); sc.add(lib['glowshroom_1'], 684, 122)
    # THE FALLEN TREE — hollow log with its torn roots, a snapped branch, moss, mushrooms in
    # its shade and a fern: a quiet corner at the clearing's south-east.
    for (nm, x, y, fl) in (('hollowlog_0', 470, 356, False), ('branch_1', 442, 372, False), ('fern_2', 502, 344, False), ('shroom_1', 446, 370, False)):
        put(nm, x, y, fl)
    sc.add(lib['glowshroom_0'], 490, 364)
    sc.decals.append(C.moss_patch(460, 360, 14, 5)); sc.decals.append(C.leaf_litter(472, 366, 24, 14))
    # THE LONE ROWAN — the meadow's landmark, with a flower ring at its foot
    ctx.place('rowan_0', 418, 186); sc.add(lib['flowers_b1'], 440, 198); sc.add(lib['flowers_w0'], 400, 196); sc.add(lib['tuft_1'], 426, 194)
    sc.add(lib['branch_0'], 236, 222)                                   # a branch fallen under the big oak, clear of the woodpile

    # ------------------------------------------------------------------ rules
    def species(band, tx, ty, r_):
        ang = math.atan2(ty - 15.5, tx - 24); north = -2.6 < ang < -0.5
        if band == 0: return r_.choice(['oak_0', 'oak_1', 'oak_2', 'oak_3', 'birch_0', 'birch_1', 'rowan_0'] if not north else ['oak_1', 'oak_3', 'pine_0', 'birch_0'])
        return r_.choice(['pine_0', 'pine_1', 'oak_0', 'oak_2', 'oak_3'] if north else ['oak_0', 'oak_1', 'birch_1', 'pine_1', 'oak_2'])
    def exclude(tx, ty):
        if ty < 4.4: return True
        if tx < 12.5 and ty < 9.5: return True                     # the stony rise is planted by hand
        if (tx > 35.5 and ty > 24.5): return True                   # so is the marsh
        for (rx, ry) in ((48, 9), (46, 11.5), (44, 13), (39.8, 21), (40.4, 23.5), (42, 25.6), (43.4, 27.6), (42.8, 29.5)):
            if math.hypot(tx - rx, ty - ry) < 4.6: return True
        # the south-west leg of the main path stays open too
        for k in range(9):
            if math.hypot(tx - (4.5 + 9 * k / 8), ty - (30.5 - 9 * k / 8)) < 2.6: return True     # the banks stay open so the river can be seen
        if 33 < tx < 44 and 2.5 < ty < 9.5: return True
        if abs(tx - (29.5 + (ty - 15.5) * -0.75)) < 1.3 and 7.5 < ty < 16: return True
        return False
    C.forest_edge(ctx, clearing_dist, species, exclude=exclude, spacing=(3.1, 2.7, 2.4))   # smaller, calmer canopies: keep the forest full
    C.understorey(ctx, clearing_dist, recipe=[('shrub_', 3, 3), ('fern_', 3, 2), ('tallgrass_', 3, 2)], n_cand=1700, spacing=1.7, band=(0.3, 2.8))      # bushes, ferns and long grass fill the gaps between edge trees
    C.pond_margin(ctx, keep=lambda x, y: not (500 < x < 600 and 250 < y < 310) and not (590 < x < 724 and 330 < y < 410))
    trees = [(p.x, p.y) for p in sc.placements if 'tree' in p.sprite.tags and 'sapling' not in p.sprite.tags]
    C.path_decorate(ctx, trees)
    C.sheltered_corner(ctx, 182, 236)              # under the big oak, beside the woodpile
    C.sheltered_corner(ctx, 112, 300)
    C.ruin_overgrowth(ctx, 556, 90, 680, 136)
    # sunny meadow: wildflowers in two loose drifts, none in the shade
    C.vegetation_cluster(ctx, 370, 352, 40, [('flowers_w', 2, 3), ('flowers_b', 2, 2), ('flowers_y', 2, 1), ('tuft_', 3, 2)], spacing=9, n=4)
    C.vegetation_cluster(ctx, 560, 380, 33, [('flowers_p', 2, 2), ('flowers_r', 2, 1), ('tallgrass_', 3, 2), ('tuft_', 3, 1)], spacing=8, n=4)
    C.vegetation_cluster(ctx, 170, 262, 24, [('flowers_w', 2, 2), ('shroom_', 2, 1), ('tuft_', 3, 1)], spacing=9, n=2)
    C.vegetation_cluster(ctx, 470, 150, 29, [('flowers_y', 2, 2), ('flowers_w', 2, 1), ('tuft_', 3, 1)], spacing=8, n=3)
    C.vegetation_cluster(ctx, 300, 150, 26, [('flowers_b', 2, 2), ('flowers_p', 2, 1), ('tallgrass_', 3, 1)], spacing=8, n=3)
    C.vegetation_cluster(ctx, 640, 400, 24, [('flowers_r', 2, 2), ('flowers_y', 2, 1)], spacing=8, n=3)
    C.foreground_frame(ctx)
    for (x, y, rx, ry) in ((176, 192, 11, 6), (150, 110, 9, 5), (660, 380, 10, 6)):
        sc.decals.append(C.moss_patch(x, y, rx, ry))
    sc.decals.append(C.pebbles(520, 280, 22, 7)); sc.decals.append(C.pebbles(330, 318, 18, 5))
    def scorch(c, r_):
        m = c.ellipse_mask(318, 276, 16, 7); ok = np.isin(c.a, PAL.ramp('grass') + PAL.ramp('worn'))
        ys, xs = np.nonzero(m & ok)
        for k in range(len(xs)):
            x, y = int(xs[k]), int(ys[k]); d = ((x - 318) / 16) ** 2 + ((y - 276) / 7) ** 2
            if d < 0.45 or (d < 0.8 and (x + y) % 2 == 0) or (d < 1 and (x * 3 + y) % 5 == 0): c.put(x, y, PAL.i('earth', 1) if d < 0.45 else PAL.i('earth', 2))
    sc.decals.append(GA.camp_ground(300, 276, 44, 22, fire=None, links=[(250, 258, 24, 10), (194, 254, 18, 10)]))
    sc.decals.append(distant_backdrop)
    sc.decals.append(GA.forest_depth())

    # ------------------------------------------------------------------ night-only
    ff = PAL.i('firefly', 0)
    for (x, y) in ((300, 330), (340, 300), (380, 340), (420, 290), (250, 300), (460, 360), (530, 330), (590, 250), (620, 290), (660, 320), (560, 300), (200, 350), (350, 400), (500, 250), (440, 390), (610, 230), (600, 430), (640, 440), (690, 425), (720, 445), (660, 455)):
        sc.night_pixels.append((x, y, ff)); sc.night_pixels.append((x + 1, y, ff))
        sc.lights.append(Light(x, y, 7, color=(0.75, 0.95, 0.55), intensity=0.55))
    eyes = PAL.i('eyes', 0)
    for (x, y) in ((118, 206), (121, 206)): sc.night_pixels.append((x, y, eyes))
    ml = PAL.ramp('moonlight')
    for (x, y, L) in ((632, 250, 3), (640, 256, 4), (628, 262, 3), (644, 268, 5), (636, 274, 3), (648, 280, 4), (640, 288, 3), (652, 294, 2)):
        for i in range(L): sc.night_pixels.append((x + i, y, ml[2] if 0 < i < L - 1 else ml[1]))
    # ------------------------------------------------------------------ lights
    sc.lights.append(Light(242, 252, 46, color=(1.0, 0.84, 0.58), intensity=0.8))
    sc.lights.append(Light(318, 262, 50, color=(1.0, 0.72, 0.42), intensity=0.95))
    sc.lights.append(Light(272, 236, 34, color=(1.0, 0.80, 0.55), intensity=0.6))
    sc.lights.append(Light(592, 262, 52, color=(1.0, 0.84, 0.58)))
    sc.lights.append(Light(612, 82, 48, color=(1.0, 0.84, 0.58), intensity=0.9))
    for (x, y) in ((596, 134), (684, 124), (500, 410)): sc.lights.append(Light(x, y, 14, color=(0.55, 0.95, 1.0), intensity=0.5))
    sc.use_meadow_pass = False
    shade_near = [(p.x + 3, p.y + 1, max(12, p.sprite.w * 0.55), 9) for p in sc.placements if 'tree' in p.sprite.tags and 'sapling' not in p.sprite.tags]
    sc.ground_passes = [GA.edge_cleanup, lambda c: GA.grass_pass(c, shade_near=shade_near), GA.path_pass]
    sc.playable = (32, 48, sc.W - 64, sc.H - 80)
    sc.paths = [main, branch]
    return sc


def distant_backdrop(c: Canvas, rng):
    """Deep forest closing the north edge: layered dark treetops, no mist band."""
    r = random.Random(5); W = c.w; pn = PAL.ramp('pine'); ok = PAL.ramp('oak')
    c.rect(0, 0, W, 44, pn[0])
    for x in range(-20, W + 20, 17):
        rad = r.randint(12, 19); yb = 26 + r.randint(-6, 6); c.ellipse(x, yb, rad, rad * .8, pn[1]); c.ellipse(x - 3, yb - 4, rad * .55, rad * .45, pn[2])
    for x in range(-10, W + 20, 21):
        rad = r.randint(15, 22); yb = 50 + r.randint(-5, 5); c.ellipse(x, yb, rad, rad * .75, ok[1]); c.ellipse(x - 4, yb - 5, rad * .6, rad * .45, ok[2]); c.ellipse(x - 6, yb - 8, rad * .3, rad * .22, ok[3])
