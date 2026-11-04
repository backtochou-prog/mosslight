"""Fast look at the campsite while working on the art: builds the library and the clearing, renders spring day
(and optionally night) and saves crops at 3x. Not part of the build.

    python3 tools/preview_camp.py [night]
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
from pixelart.terrain_tiles import TerrainTiles
from pixelart.objects import build_library, build_library_extended
from pixelart.scene_clearing import build
t0 = time.time()
tiles = TerrainTiles(); lib = build_library_extended(build_library()); sc = build(lib)
night = 'night' in sys.argv[1:]
season = next((a for a in sys.argv[1:] if a in ('summer', 'autumn', 'winter')), 'spring')
if season == 'winter': sc.mm.snow_everywhere(coverage=0.92, shelter=[(p.x, p.y, 26) for p in sc.placements if 'tree' in p.sprite.tags and 'sapling' not in p.sprite.tags])
c, rgb = sc.render(tiles, night=night, season=season)
def sat(a, k=1.28):
    a = a.astype(np.float32); l = (a * [0.299, 0.587, 0.114]).sum(-1, keepdims=True); return np.clip(l + (a - l) * k, 0, 255).astype(np.uint8)
rgb = sat(rgb)          # the game adds this saturation at runtime
tag = ('night' if night else 'day') + ('' if season == 'spring' else '_' + season)
Image.fromarray(rgb).save(f'/tmp/camp_full_{tag}.png')
for nm, (x0, y0, x1, y1) in {'camp': (140, 160, 470, 360), 'fire': (230, 200, 400, 320)}.items():
    Image.fromarray(rgb[y0:y1, x0:x1]).resize(((x1 - x0) * 3, (y1 - y0) * 3), Image.NEAREST).save(f'/tmp/camp_{nm}_{tag}.png')
print('built in', round(time.time() - t0, 1), 's')
