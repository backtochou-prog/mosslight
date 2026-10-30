"""Build everything: tiles, sprites, scenes, renders, data exports."""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(__file__))
from pixelart.terrain_tiles import TerrainTiles, MATERIALS
from pixelart.objects import build_library, build_library_extended
from pixelart.scene_clearing import build as build_clearing
from pixelart.scene_terrain_test import build as build_test
from pixelart.render import save_rgb
from pixelart.palette import PAL, FAMILIES, SEASON_OVERRIDES
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
t0 = time.time()
tiles = TerrainTiles(); tiles.export(os.path.join(ROOT, 'assets/tiles'))
lib = build_library_extended(build_library())
objdir = os.path.join(ROOT, 'assets/objects'); os.makedirs(objdir, exist_ok=True)
import numpy as np
CANOPY_FAMS = {'oak', 'birch', 'pine', 'rowan', 'shrub'}
def trunk_top(s):
    """For trees: first row (from the bottom) that holds canopy pixels. Rows
    below it are trunk/roots = the solid, player-blocking part; rows above it
    are canopy the player can walk behind."""
    if 'tree' not in s.tags: return None
    fams = np.array([PAL.family_of(int(i)) in CANOPY_FAMS for i in range(len(PAL.entries))])
    rows = np.nonzero(fams[s.c.a].any(axis=1))[0]
    return int(rows.max()) + 1 if len(rows) else None
meta = {}
for name, s in lib.items():
    s.c.save(os.path.join(objdir, name + '.png'))
    meta[name] = {'w': s.w, 'h': s.h, 'origin': [s.ox, s.oy], 'shadow': s.shadow, 'tags': list(s.tags),
                  'solid': any(t in s.tags for t in ('tree', 'rock', 'structure', 'solid')) and 'sapling' not in s.tags,
                  'trunk_top': trunk_top(s)}
json.dump(meta, open(os.path.join(objdir, 'objects.json'), 'w'), indent=1)
# season / biome data for the engine
sdir = os.path.join(ROOT, 'assets/seasons'); os.makedirs(sdir, exist_ok=True)
for season in SEASON_OVERRIDES:
    for night in (False, True):
        lut = PAL.lut(season, night)
        json.dump({'season': season, 'night': night, 'entries': [{'family': f, 'rank': r, 'rgb': list(lut[i])} for i, (f, r) in enumerate(PAL.entries)]},
                  open(os.path.join(sdir, f'{season}_{"night" if night else "day"}.json'), 'w'))
bdir = os.path.join(ROOT, 'assets/biomes'); os.makedirs(bdir, exist_ok=True)
json.dump({
    'name': 'temperate_forest', 'label': 'Lush temperate forest (the first clearing)',
    'materials': ['grass', 'worn', 'forest', 'dirt', 'earth', 'pebble', 'mud', 'stone', 'mossy', 'paved', 'shallow', 'water', 'sand'],
    'trees': {'edge': ['oak_0', 'oak_1', 'oak_2', 'oak_3', 'birch_0', 'birch_1', 'rowan_0'], 'north': ['oak_1', 'oak_3', 'pine_0', 'birch_0'], 'deep': ['pine_0', 'pine_1', 'oak_0', 'oak_2', 'oak_3'], 'water': ['willow_0', 'willow_1']},
    'understorey': ['shrub_0', 'shrub_1', 'shrub_2', 'fern_0', 'fern_1', 'fern_2', 'tallgrass_0', 'tallgrass_1', 'tallgrass_2', 'sapling_oak0', 'sapling_birch0'],
    'meadow': ['flowers_w0', 'flowers_w1', 'flowers_b0', 'flowers_y0', 'flowers_p0', 'flowers_r0', 'tuft_0', 'tuft_1', 'tuft_2'],
    'shore': ['reeds_0', 'reeds_1', 'arrowhead_0', 'arrowhead_1', 'lily_0', 'lily_1', 'lily_2', 'lily_3', 'stone_0', 'stone_1'],
    'rules': ['forest_edge', 'understorey', 'pond_margin', 'path_decorate', 'sheltered_corner', 'ruin_overgrowth', 'vegetation_cluster', 'foreground_frame'],
    'seasons': {'spring': {'lut': 'spring_day.json', 'litter': 0.6}, 'summer': {'lut': 'summer_day.json', 'litter': 0.3},
                'autumn': {'lut': 'autumn_day.json', 'litter': 1.8}, 'winter': {'lut': 'winter_day.json', 'litter': 0.0, 'snow_coverage': 0.85, 'sprite_suffix': '_winter'}},
}, open(os.path.join(bdir, 'temperate_forest.json'), 'w'), indent=1)
planned = {'planned_biomes': [
    {'name': 'abandoned_village', 'atmosphere': 'overgrown lanes, paved + earth, hedges, fruit trees, warm ruins'},
    {'name': 'misty_marsh', 'atmosphere': 'mud, shallow water, reeds, willows, mist layer, cool palette'},
    {'name': 'rocky_highland', 'atmosphere': 'stone + mossy stone, pines, sparse grass, strong shadows'},
    {'name': 'ruined_city', 'atmosphere': 'paved everywhere, cracked, saplings in rubble, ivy'},
    {'name': 'frozen_forest', 'atmosphere': 'winter tables + snow, bare trees, ice'},
    {'name': 'night_wetland', 'atmosphere': 'night-first palette, glow plants, fireflies, deep water'}],
    'note': 'each biome = material subset + species lists + rule parameters + palette overrides, same engine data layout as temperate_forest.json'}
json.dump(planned, open(os.path.join(bdir, 'planned.json'), 'w'), indent=1)

out = os.path.join(ROOT, 'renders')
# -- the clearing: spring day/night, autumn, winter
sc = build_clearing(lib)
sc.export_json(os.path.join(ROOT, 'scene/forest_clearing.json'))
for night in (False, True):
    c, rgb = sc.render(tiles, night=night, season='spring')
    tag = 'night' if night else 'day'
    save_rgb(rgb, f'{out}/clearing_{tag}_1x.png'); save_rgb(rgb, f'{out}/clearing_{tag}_3x.png', 3)
    for (nm, x, y) in (('camp', 60, 90), ('pond', 128, 60)):
        save_rgb(rgb[y:y + 360, x:x + 640], f'{out}/view_{nm}_{tag}_2x.png', 2)
c, rgb = sc.render(tiles, night=False, season='autumn'); save_rgb(rgb, f'{out}/clearing_autumn_1x.png')
shel = [(p.x, p.y, 26) for p in sc.placements if 'tree' in p.sprite.tags and 'sapling' not in p.sprite.tags]
sc.mm.snow_everywhere(coverage=0.92, shelter=shel)
c, rgb = sc.render(tiles, night=False, season='winter'); save_rgb(rgb, f'{out}/clearing_winter_1x.png'); save_rgb(rgb[90:450, 60:700], f'{out}/view_camp_winter_2x.png', 2)
c, rgb = sc.render(tiles, night=True, season='winter'); save_rgb(rgb, f'{out}/clearing_winter_night_1x.png')
# -- layering check: scale figures behind the big oak's trunk, by the tent, on the dock
from pixelart.render import Placement
extra = [Placement(lib['mannequin'], 222, 200), Placement(lib['mannequin'], 262, 268), Placement(lib['mannequin'], 566, 296), Placement(lib['mannequin'], 700, 214)]
sc2 = build_clearing(lib)
c, rgb = sc2.render(tiles, night=False, season='spring', debug_extra=extra)
save_rgb(rgb[150:330, 150:470], f'{out}/check_layering_scale_4x.png', 4)
save_rgb(rgb[150:330, 520:768], f'{out}/check_layering_willow_4x.png', 4)
# -- terrain test scene
ts = build_test(lib)
ts.export_json(os.path.join(ROOT, 'scene/terrain_test.json'))
c, rgb = ts.render(tiles, season='spring'); save_rgb(rgb, f'{out}/terrain_test_spring_1x.png'); save_rgb(rgb, f'{out}/terrain_test_spring_3x.png', 3)
ts.mm.snow_everywhere(coverage=0.92, shelter=[(p.x, p.y, 26) for p in ts.placements if 'tree' in p.sprite.tags and 'sapling' not in p.sprite.tags])
c, rgb = ts.render(tiles, season='winter'); save_rgb(rgb, f'{out}/terrain_test_winter_1x.png'); save_rgb(rgb, f'{out}/terrain_test_winter_3x.png', 3)
print('rendered in', round(time.time() - t0, 1), 's;', len(lib), 'sprites;', len(MATERIALS), 'materials')
