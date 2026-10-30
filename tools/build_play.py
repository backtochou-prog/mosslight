"""Export everything the exploration build needs: player sheet, depth maps,
collision mask, interactables, shade table."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
from pixelart.terrain_tiles import TerrainTiles
from pixelart.objects import build_library, build_library_extended
from pixelart.scene_clearing import build
from pixelart.palette import PAL
from pixelart.canvas import Canvas
from pixelart import player

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.join(ROOT, 'assets/play'); os.makedirs(out, exist_ok=True)
sheet, pmeta = player.export(out)
tiles = TerrainTiles(); lib = build_library_extended(build_library())
sc = build(lib)
W, H = sc.W, sc.H

# ---- depth map: base y of the frontmost y-sorted sprite per pixel (0 = ground, 65535 = foreground)
def depth_map(season):
    sc.season = season
    d = np.zeros((H, W), dtype=np.uint16)
    ysort = [p for p in sc.placements if p.layer == 'ysort']
    for p in sorted(ysort, key=lambda p: (p.y, p.x)):
        s = sc.resolve(p.sprite)
        if s is None: continue
        ox = (s.w - 1 - s.ox) if p.flip else s.ox
        x0, y0 = p.x - ox, p.y - s.oy
        a = s.c.a[:, ::-1] if p.flip else s.c.a
        for yy in range(max(0, y0), min(H, y0 + s.h)):
            row = a[yy - y0]
            xs = np.nonzero(row)[0] + x0
            xs = xs[(xs >= 0) & (xs < W)]
            d[yy, xs] = p.y
    for p in [p for p in sc.placements if p.layer == 'fg']:
        s = sc.resolve(p.sprite)
        if s is None: continue
        ox = (s.w - 1 - s.ox) if p.flip else s.ox
        x0, y0 = p.x - ox, p.y - s.oy
        a = s.c.a[:, ::-1] if p.flip else s.c.a
        for yy in range(max(0, y0), min(H, y0 + s.h)):
            xs = np.nonzero(a[yy - y0])[0] + x0; xs = xs[(xs >= 0) & (xs < W)]
            d[yy, xs] = 65535
    rgb = np.dstack([(d & 255).astype(np.uint8), (d >> 8).astype(np.uint8), np.zeros((H, W), np.uint8)])
    Image.fromarray(rgb, 'RGB').save(os.path.join(out, f'depth_{season}.png'))
depth_map('spring'); depth_map('winter')

# ---- collision mask: 1 = blocked
col = np.zeros((H, W), dtype=np.uint8)
c = sc.render_indexed(tiles, night=False, season='spring')
water = np.isin(c.a, PAL.ramp('water'))
# erode water by 2 px so the player can stand on the bank
for _ in range(2):
    p = np.pad(water, 1); water = water & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
col[water] = 1
objmeta = json.load(open(os.path.join(ROOT, 'assets/objects/objects.json')))
def ellipse(cx, cy, rx, ry, val=1):
    m = Canvas(W, H); m.ellipse(cx, cy, rx, ry, 1); col[m.a == 1] = val
def rect(x0, y0, x1, y1, val=1):
    col[max(0, y0):min(H, y1), max(0, x0):min(W, x1)] = val
for p in sc.placements:
    s = p.sprite; nm = s.name; meta = objmeta.get(nm, {})
    if not meta.get('solid') or p.layer == 'fg': continue
    tags = s.tags
    if nm == 'dock':
        rect(p.x - 2, p.y - 18, p.x + 45, p.y - 2, 0)          # the deck is walkable, over water
        rect(p.x + 41, p.y - 22, p.x + 45, p.y - 14, 1)          # mooring post
        continue
    if 'tree' in tags:
        ellipse(p.x, p.y - 1, max(5, s.w // 9), 3)
    elif nm == 'tent':
        rect(p.x - 21, p.y - 20, p.x + 22, p.y - 2)
    elif nm == 'ruin_back':
        rect(p.x - 46, p.y - 12, p.x + 47, p.y + 1); rect(p.x - 13, p.y - 12, p.x + 6, p.y + 1, 0)   # doorway stays open
    elif nm == 'ruin_side':
        rect(p.x - 5, p.y - 48, p.x + 6, p.y + 1)
    elif s.shadow:
        rx, ry, dx, dy = s.shadow; ellipse(p.x + dx * 0.3, p.y - 1, max(3, rx * 0.85), max(2, ry))
# world border: outside the playable rect is blocked
px0, py0, pw, ph = sc.playable
col[:py0, :] = 1; col[py0 + ph:, :] = 1; col[:, :px0] = 1; col[:, px0 + pw:] = 1
Image.fromarray(col * 255, 'L').save(os.path.join(out, 'collision.png'))

# ---- interactables: driven by data, not by the player script
inter = [
    {'id': 'tent', 'label': 'Inspect tent', 'x': 272, 'y': 246, 'r': 30, 'text': 'A worn canvas tent. The flap is rolled back; your bedroll is inside.'},
    {'id': 'lantern', 'label': 'Inspect lantern', 'x': 240, 'y': 262, 'r': 18, 'text': 'An oil lantern on a crooked post. It will burn through the night.'},
    {'id': 'campfire', 'label': 'Tend the fire', 'x': 318, 'y': 272, 'r': 22, 'text': 'A small fire in a ring of stones. The embers are still warm.'},
    {'id': 'dock', 'label': 'Look at the pond', 'x': 562, 'y': 288, 'r': 30, 'text': 'A weathered fishing platform. Something stirs under the lily pads.'},
    {'id': 'ruin', 'label': 'Examine the ruins', 'x': 612, 'y': 108, 'r': 34, 'text': 'Two walls and a lintel, taken back by moss. Someone hung a lantern here recently.'},
    {'id': 'log', 'label': 'Peer into the log', 'x': 480, 'y': 404, 'r': 22, 'text': 'A hollow log, soft with rot. Mushrooms grow in its shade.'},
    {'id': 'rowan', 'label': 'Rowan tree', 'x': 418, 'y': 188, 'r': 18, 'text': 'A young rowan alone in the meadow, heavy with red berries.'},
]
json.dump({'width': W, 'height': H, 'playable': sc.playable, 'spawn': [300, 318], 'interactables': inter,
           'depth': {'spring': 'depth_spring.png', 'summer': 'depth_spring.png', 'autumn': 'depth_spring.png', 'winter': 'depth_winter.png'},
           'collision': 'collision.png', 'player': 'player.json', 'shade': PAL.shade}, open(os.path.join(out, 'play.json'), 'w'))
print('play exported:', sorted(os.listdir(out)), 'blocked %:', round(col.mean() * 100, 1))
