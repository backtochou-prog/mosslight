"""Environmental composition rules.

Reusable, deterministic (seeded) rules that place vegetation and ground
decals by ecological and compositional logic. Every rule respects an
Occupancy map (no overlapping solid footprints), keep-out zones (paths,
water, entrances) and a density cap. Landmarks stay hand-placed; rules fill
the world *around* them.

Rules:
  forest_edge        tree bands around a clearing, species by compass direction
  pond_margin        reeds / arrowheads / lilies / bank stones by shoreline analysis
  path_decorate      roots where trees crowd the path, stones at bends, tufts on wide stretches
  vegetation_cluster weighted species cluster in a region (ferns, flowers, tall grass ...)
  sheltered_corner   ferns + mushrooms + moss tucked against a big tree or rock
  ruin_overgrowth    moss, litter, saplings reclaiming a structure
  foreground_frame   canopies and ferns leaning into the bottom corners
Decals: moss_patch, pebbles, leaf_litter (ground-layer pixel decals).
"""
from __future__ import annotations
import math, random
import numpy as np
from .canvas import Canvas
from .palette import PAL
from .terrain_tiles import T, GRASS, WORN, FOREST, SAND, DIRT, EARTH, PEBBLE, MUD, STONE, MOSSY, PAVED, SHALLOW, WATER
from .render import Scene, Placement

# ---------------------------------------------------------------------------
# occupancy + keep-out
# ---------------------------------------------------------------------------
class Occupancy:
    """Circles (px) that solid footprints occupy."""
    def __init__(self):
        self.items = []
    def add(self, x, y, r):
        self.items.append((x, y, r))
    def free(self, x, y, r, margin=2):
        for (px, py, pr) in self.items:
            if math.hypot(px - x, py - y) < pr + r + margin: return False
        return True

def footprint_radius(sprite):
    if sprite.shadow: return max(3, int(sprite.shadow[0] * 0.7))
    return max(3, sprite.w // 3)

class Context:
    """Shared state for the rules: scene, library, rng, occupancy, keep-out tests."""
    def __init__(self, scene: Scene, lib: dict, seed: int, paths=(), keepouts=()):
        self.sc, self.lib, self.rng = scene, lib, random.Random(seed)
        self.occ = Occupancy()
        self.paths = list(paths)
        self.keepouts = list(keepouts)       # (x, y, r) px circles that stay empty
        self.mm = scene.mm

    def ground(self, x, y):
        tx, ty = x / T, y / T
        return self.mm.vertex_mat(tx, ty)

    def on_path(self, x, y, margin=0.6):
        for p in self.paths:
            d, w = p.nearest(x / T, y / T)
            if d < w + margin: return True
        return False

    def in_keepout(self, x, y):
        return any(math.hypot(x - kx, y - ky) < kr for (kx, ky, kr) in self.keepouts)

    def is_water(self, x, y):
        return self.ground(x, y) >= SHALLOW

    def place(self, name, x, y, flip=None, layer='ysort', solid=None, night_only=False):
        s = self.lib[name]
        if flip is None: flip = self.rng.random() < 0.5
        solid = ('solid' in s.tags or 'tree' in s.tags or 'rock' in s.tags or 'structure' in s.tags) if solid is None else solid
        r = footprint_radius(s)
        if solid:
            if not self.occ.free(x, y, r): return None
            self.occ.add(x, y, r)
        return self.sc.add(s, int(x), int(y), flip=flip, layer=layer, night_only=night_only)

    def reserve(self, x, y, r):
        self.occ.add(x, y, r)

# ---------------------------------------------------------------------------
# decals
# ---------------------------------------------------------------------------
def moss_patch(cx, cy, rx, ry):
    def d(c, r_):
        m = c.ellipse_mask(cx, cy, rx, ry)
        ok = np.isin(c.a, PAL.ramp('grass') + PAL.ramp('forest') + PAL.ramp('dirt')[:4] + PAL.ramp('stone')[:4])
        mo = PAL.ramp('moss')
        core = c.ellipse_mask(cx, cy, rx * 0.6, ry * 0.6)
        ys, xs = np.nonzero(m & ok)
        for k in range(len(xs)):
            x, y = int(xs[k]), int(ys[k])
            if core[y, x] or (x * 3 + y * 5) % 4 == 0:
                c.put(x, y, mo[0] if (x + y) % 3 else mo[1])
    return d

def pebbles(cx, cy, r, n):
    def d(c, r_):
        m = c.ellipse_mask(cx, cy, r, r * 0.6)
        ok = np.isin(c.a, PAL.ramp('dirt') + PAL.ramp('mud') + PAL.ramp('worn') + PAL.ramp('earth') + PAL.ramp('sand'))
        pb = PAL.ramp('pebble')
        ys, xs = np.nonzero(m & ok)
        if not len(xs): return
        for _ in range(n):
            k = r_.randrange(len(xs)); x, y = int(xs[k]), int(ys[k])
            c.put(x, y, pb[1]); c.put(x + 1, y, pb[0])
            if r_.random() < 0.4: c.put(x, y - 1, pb[2])
    return d

def leaf_litter(cx, cy, r, n):
    def d(c, r_):
        m = c.ellipse_mask(cx, cy, r, r * 0.6)
        ok = np.isin(c.a, PAL.ramp('grass') + PAL.ramp('forest'))
        ll = PAL.ramp('leaf_litter')
        ys, xs = np.nonzero(m & ok)
        if not len(xs): return
        for _ in range(n):
            k = r_.randrange(len(xs)); x, y = int(xs[k]), int(ys[k])
            c.put(x, y, ll[r_.choice((1, 2, 2, 3))]); c.put(x + 1, y, ll[r_.choice((1, 2))])
    return d

# ---------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------
def poisson(ctx: Context, accept, n_cand, spacing_fn, order=None):
    """Rejection sampling: candidates filtered by `accept(tx, ty)` (tile
    coords), sorted by `order`, kept if farther than `spacing_fn(tx, ty)`
    from every kept point."""
    rng = ctx.rng; W, H = ctx.mm.w, ctx.mm.h
    cand = []
    for _ in range(n_cand):
        tx, ty = rng.uniform(0.5, W - 0.5), rng.uniform(0.5, H + 1.5)
        v = accept(tx, ty)
        if v is None: continue
        cand.append((v if order else 0, tx, ty))
    cand.sort(key=lambda c: c[0])
    kept = []
    for (_, tx, ty) in cand:
        sp = spacing_fn(tx, ty)
        if all(math.hypot(tx - kx, ty - ky) >= sp for (kx, ky) in kept):
            kept.append((tx, ty))
    return kept

def forest_edge(ctx: Context, clearing_dist, species_by_band, n_cand=3000, spacing=(2.7, 2.4, 2.3), min_edge=0.9, exclude=lambda tx, ty: False):
    """clearing_dist(tx,ty): <0 inside the clearing, >0 in the woods (tiles).
    species_by_band(band, tx, ty, rng) -> sprite name. Band 0 = clearing edge."""
    def accept(tx, ty):
        d = clearing_dist(tx, ty)
        if d < min_edge or exclude(tx, ty): return None
        if ctx.mm.vertex_mat(tx, ty) >= SHALLOW: return None
        if ctx.on_path(tx * T, ty * T, margin=0.9): return None
        return d
    def sp(tx, ty):
        d = clearing_dist(tx, ty)
        return spacing[0 if d < 2.6 else (1 if d < 5.5 else 2)]
    H = ctx.mm.h
    for (tx, ty) in poisson(ctx, accept, n_cand, sp, order=True):
        d = clearing_dist(tx, ty); band = 0 if d < 2.6 else (1 if d < 5.5 else 2)
        name = species_by_band(band, tx, ty, ctx.rng)
        ctx.place(name, tx * T, ty * T, layer='fg' if ty > H - 0.6 else 'ysort')

def shoreline(mm, band=MUD):
    """Tile-space points along the water edge with an outward normal."""
    pts = []
    for vy in range(mm.h + 1):
        for vx in range(mm.w + 1):
            if mm.m[vy, vx] < SHALLOW: continue
            nx = ny = 0; land = False
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ux, uy = vx + dx, vy + dy
                if 0 <= ux <= mm.w and 0 <= uy <= mm.h and mm.m[uy, ux] < SHALLOW:
                    land = True; nx += dx; ny += dy
            if land:
                L = math.hypot(nx, ny) or 1
                pts.append((vx, vy, nx / L, ny / L))
    return pts

def pond_margin(ctx: Context, reed_density=0.45, lily_density=0.35, keep=lambda x, y: True):
    """Reeds on the far (north) and side banks, arrowheads in shallow water,
    lily pads in the sheltered water, a few stones on the mud bank, grass
    tufts on the near bank. Never on the dock approach (use `keep`)."""
    rng = ctx.rng; mm = ctx.mm
    shore = shoreline(mm)
    for (vx, vy, nx, ny) in shore:
        px, py = vx * T, vy * T
        if not keep(px, py): continue
        if ny < -0.3 or abs(nx) > 0.6:            # far bank and side banks: reeds stand in the shallows
            if rng.random() < reed_density:
                ctx.place(f'reeds_{rng.randrange(2)}', px + rng.randint(-4, 4) - int(nx * 6), py + rng.randint(-2, 2) - int(ny * 6) + 8, solid=False)
        elif ny > 0.3:                            # near bank: tufts and a bank stone
            if rng.random() < 0.35:
                ctx.place(f'tuft_{rng.randrange(3)}', px + rng.randint(-6, 6), py + rng.randint(6, 12), solid=False)
            if rng.random() < 0.15:
                ctx.place(f'stone_{rng.randrange(2)}', px + rng.randint(-6, 6), py + rng.randint(4, 10), solid=False)
        if rng.random() < 0.12:
            ctx.place(f'arrowhead_{rng.randrange(2)}', px - int(nx * 10), py - int(ny * 10) + 6, solid=False)
    # lily pads: sheltered water within ~2 vertices of the shore, in small
    # rafts of 2-4 pads, biased to the north-east (away from the dock side)
    land = mm.m < SHALLOW
    water_cells = [(vx, vy) for vy in range(mm.h + 1) for vx in range(mm.w + 1) if mm.m[vy, vx] >= SHALLOW]
    def near_shore(vx, vy):
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                ux, uy = vx + dx, vy + dy
                if 0 <= ux <= mm.w and 0 <= uy <= mm.h and land[uy, ux]: return True
        return False
    cells = [cv for cv in water_cells if near_shore(*cv)]
    rng.shuffle(cells)
    n = max(2, int(len(cells) * lily_density * 0.22))
    for (vx, vy) in cells[:n]:
        px, py = vx * T, vy * T
        if not keep(px, py): continue
        for k in range(rng.randint(2, 4)):
            x, y = px + rng.randint(-9, 9), py + rng.randint(-7, 7)
            if ctx.ground(x, y) >= SHALLOW:
                ctx.place(f'lily_{rng.randrange(4)}', x, y, layer='ground', solid=False)

def path_decorate(ctx: Context, trees, stone_density=0.6):
    """Roots where a tree stands within reach of the path; stone clusters at
    sharp bends; grass tuft patches where the path is wide."""
    rng = ctx.rng
    for p in ctx.paths:
        for (x, y, w) in p.samples()[::2]:
            for (tx_px, ty_px) in trees:
                d = math.hypot(tx_px - x * T, ty_px - y * T)
                if 14 < d < 30 and rng.random() < 0.5:
                    ctx.place(f'roots_{rng.randrange(2)}', tx_px, ty_px - 2, layer='ground', solid=False, flip=tx_px > x * T)
        for i in p.curvature_points():
            x, y, w = p.samples()[i]
            if rng.random() < stone_density:
                ctx.sc.decals.append(pebbles(x * T + rng.randint(-6, 6), y * T + rng.randint(-6, 6), 10, 5))
        for (x, y, w) in p.samples()[::6]:
            if w > 1.05 and rng.random() < 0.35:
                ctx.place(f'tuft_{rng.randrange(3)}', x * T + rng.randint(-10, 10), y * T + rng.randint(-8, 8), solid=False)

def vegetation_cluster(ctx: Context, cx, cy, r, recipe, spacing=10, n=None, layer='ysort', accept=None):
    """recipe: [(sprite_prefix, variants, weight)]. Places ~n sprites in a disc
    (px), densest at the centre, never on paths/water/keep-outs."""
    rng = ctx.rng
    names, weights = [], []
    for (prefix, variants, w) in recipe:
        for v in range(variants): names.append(f'{prefix}{v}'); weights.append(w / variants)
    n = n or max(2, int(r * r / (spacing * spacing * 2.2)))
    placed = []
    for _ in range(n * 6):
        if len(placed) >= n: break
        a = rng.uniform(0, math.tau); d = r * math.sqrt(rng.random()) * 0.95
        x, y = cx + math.cos(a) * d, cy + math.sin(a) * d * 0.7
        if ctx.on_path(x, y) or ctx.is_water(x, y) or ctx.in_keepout(x, y): continue
        if accept and not accept(x, y): continue
        if any(math.hypot(x - px, y - py) < spacing for (px, py) in placed): continue
        nm = rng.choices(names, weights)[0]
        if nm in ctx.lib and ctx.place(nm, x, y, layer=layer, solid=False) is not None: placed.append((x, y))
    return placed

def sheltered_corner(ctx: Context, x, y, r=26):
    """Ferns and mushrooms tucked into the shade at (x, y), moss on the ground."""
    ctx.sc.decals.append(moss_patch(x, y + 4, r * 0.5, r * 0.25))
    vegetation_cluster(ctx, x, y, r, [('fern_', 3, 3), ('shroom_', 2, 1), ('tallgrass_', 3, 1)], spacing=12)

def ruin_overgrowth(ctx: Context, x0, y0, x1, y1):
    """Moss, litter and a sapling or two reclaiming the walls' feet."""
    rng = ctx.rng
    for _ in range(3):
        ctx.sc.decals.append(moss_patch(rng.randint(x0, x1), rng.randint(y0, y1), rng.randint(8, 14), rng.randint(4, 7)))
    ctx.sc.decals.append(leaf_litter((x0 + x1) // 2, y1 + 6, (x1 - x0) // 2, 10))
    vegetation_cluster(ctx, (x0 + x1) // 2, y1 + 8, (x1 - x0) // 2, [('fern_', 3, 2), ('glowshroom_', 2, 1), ('tallgrass_', 3, 1), ('sapling_oak', 2, 1)], spacing=14, n=5)

def foreground_frame(ctx: Context):
    """Canopies and ferns whose bases sit below the frame lean into the corners."""
    W, H = ctx.sc.W, ctx.sc.H
    ctx.place('oak_2', 64, H + 30, layer='fg', solid=False); ctx.place('oak_1', W - 68, H + 26, flip=True, layer='fg', solid=False)
    ctx.place('fern_0', 120, H + 2, layer='fg', solid=False); ctx.place('fern_2', 150, H + 6, flip=True, layer='fg', solid=False)
    ctx.place('shrub_1', W - 8, H - 20, layer='fg', solid=False)

def understorey(ctx: Context, clearing_dist, recipe=None, n_cand=900, spacing=1.6, band=(0.2, 2.4)):
    """Shrubs, ferns and tall grass in the gaps between the edge trees."""
    recipe = recipe or [('shrub_', 3, 3), ('fern_', 3, 3), ('tallgrass_', 3, 2), ('sapling_oak', 2, 1), ('sapling_birch', 2, 1)]
    rng = ctx.rng
    names, weights = [], []
    for (prefix, variants, w) in recipe:
        for v in range(variants): names.append(f'{prefix}{v}'); weights.append(w / variants)
    def accept(tx, ty):
        d = clearing_dist(tx, ty)
        if not (band[0] <= d <= band[1]): return None
        if ctx.mm.vertex_mat(tx, ty) >= SHALLOW or ctx.on_path(tx * T, ty * T, 0.8) or ctx.in_keepout(tx * T, ty * T): return None
        return d
    for (tx, ty) in poisson(ctx, accept, n_cand, lambda a, b: spacing, order=True):
        nm = rng.choices(names, weights)[0]
        ctx.place(nm, tx * T, ty * T)

def season_sprite(lib: dict, name: str, season: str):
    """Stable identity, seasonal appearance: resolve a sprite name for a season."""
    if season == 'summer':
        swap = {'flowers_w0': 'flowers_y0', 'flowers_w1': 'flowers_y1', 'flowers_b0': 'flowers_r0', 'flowers_b1': 'flowers_r1', 'hedge_0': 'hedge_1'}
        return lib[swap.get(name, name)]
    if season != 'winter': return lib[name]
    if name.startswith(('flowers_', 'lily_', 'arrowhead_', 'shroom_')): return None   # gone under snow / ice
    if name + '_winter' in lib: return lib[name + '_winter']
    base = name.split('_')[0]
    if base == 'willow': return lib[f'willow_winter_{int(name[-1]) % 2}']
    if base == 'oak': return lib[f'oak_winter_{int(name[-1]) % 2}']
    if base in ('birch', 'rowan'): return lib[f'birch_winter_{int(name[-1]) % 2}']
    if base == 'sapling': return lib['sapling_birch0'] if 'birch' in name else lib['sapling_oak0']
    return lib[name]
