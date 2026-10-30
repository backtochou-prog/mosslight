"""Export everything the live viewer / engine needs for time, season, weather:
atmosphere tables, indexed scene layers per season, lights, night pixels."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
from pixelart.terrain_tiles import TerrainTiles
from pixelart.objects import build_library, build_library_extended
from pixelart.scene_clearing import build
from pixelart import atmosphere
from pixelart.canvas import Canvas
from pixelart.palette import PAL

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.join(ROOT, 'assets/atmosphere'); os.makedirs(out, exist_ok=True)
atmosphere.export(out)
tiles = TerrainTiles(); lib = build_library_extended(build_library())
from pixelart.render import Placement
layers = {}; shadows = {}; events = {}
EVENTS = {n: json.load(open(os.path.join(ROOT, 'assets/events', n + '.json'))) for n in ('winter_fishing', 'autumn_gathering', 'summer_pond_evening', 'marsh_night')}
def make_scene(season, props=None):
    sc = build(lib)
    if props:
        sc.extra_placements = [Placement(lib[pr['sprite']], pr['x'], pr['y'], layer=pr.get('layer', 'ysort')) for pr in props if pr['sprite'] in lib]
    if season == 'winter':
        shel = [(p.x, p.y, 26) for p in sc.placements if 'tree' in p.sprite.tags and 'sapling' not in p.sprite.tags]
        sc.mm.snow_everywhere(coverage=0.92, shelter=shel)
    return sc
for season in ('spring', 'summer', 'autumn', 'winter'):
    sc = make_scene(season)
    sc.shadows_baked = False                                  # shadows are a live layer (length follows the sun)
    c = sc.render_indexed(tiles, night=False, season=season)
    Image.fromarray(c.a, 'L').save(os.path.join(out, f'scene_{season}_idx.png'))
    for tag, (st, dx) in {'noon': (1.0, 0), 'long': (2.1, 14)}.items():
        Image.fromarray(sc.shadow_mask(st, dx, season).a, 'L').save(os.path.join(out, f'shadow_{season}_{tag}.png'))
    shadows[season] = {'noon': f'shadow_{season}_noon.png', 'long': f'shadow_{season}_long.png'}
for name, ev in EVENTS.items():
    if not ev.get('props'): continue
    sc = make_scene(ev['season'], ev['props']); sc.shadows_baked = False
    c = sc.render_indexed(tiles, night=False, season=ev['season'])
    Image.fromarray(c.a, 'L').save(os.path.join(out, f'scene_event_{name}_idx.png'))
    Image.fromarray(sc.shadow_mask(1.0, 0, ev['season']).a, 'L').save(os.path.join(out, f'shadow_event_{name}_noon.png'))
    Image.fromarray(sc.shadow_mask(2.1, 14, ev['season']).a, 'L').save(os.path.join(out, f'shadow_event_{name}_long.png'))
    events[name] = {'layer': f'scene_event_{name}_idx.png', 'noon': f'shadow_event_{name}_noon.png', 'long': f'shadow_event_{name}_long.png'}
sc = make_scene('spring')
nl = Canvas(sc.W, sc.H)
for (x, y, idx) in sc.night_pixels: nl.put(x, y, idx)
Image.fromarray(nl.a, 'L').save(os.path.join(out, 'scene_night_layer_idx.png'))
for season in ('spring', 'summer', 'autumn', 'winter'): layers[season] = f'scene_{season}_idx.png'
json.dump({'width': sc.W, 'height': sc.H, 'layers': layers, 'shadows': shadows, 'events': events, 'shade': PAL.shade, 'shade2': PAL.shade2, 'night_layer': 'scene_night_layer_idx.png',
           'lights': [{'x': L.x, 'y': L.y, 'radius': L.radius, 'color': L.color, 'intensity': L.intensity,
                       'kind': 'firefly' if L.radius <= 7 else ('glow' if L.radius <= 14 else ('fire' if abs(L.color[1] - 0.72) < 0.01 else 'lantern'))} for L in sc.lights],
           'playable': sc.playable}, open(os.path.join(out, 'scene.json'), 'w'))
print('atmosphere exported:', sorted(os.listdir(out)))
