"""Creature atlas + data + gallery; rebuilds the node atlas (now with night-resource sprites)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image
from pixelart.canvas import Canvas
from pixelart.palette import PAL
from pixelart import monsters as M
from pixelart.objects import node_sprites
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(ROOT, 'assets/monsters'); os.makedirs(OUT, exist_ok=True)
spr = M.all_sprites(); AW = 400; x = y = rh = 0; pos = {}
for nm, (c, ox, oy) in sorted(spr.items(), key=lambda kv: -kv[1][0].h):
    if x + c.w > AW: x = 0; y += rh; rh = 0
    pos[nm] = dict(x=x, y=y, w=c.w, h=c.h, ox=ox, oy=oy); x += c.w; rh = max(rh, c.h)
sheet = Canvas(AW, y + rh)
for nm, (c, _, _) in spr.items(): sheet.blit(c, pos[nm]['x'], pos[nm]['y'])
Image.fromarray(sheet.a, 'L').save(os.path.join(OUT, 'monsters_idx.png')); json.dump({'width': AW, 'index': pos}, open(os.path.join(OUT, 'monsters_atlas.json'), 'w'))
# node atlas
ns = node_sprites(); cols, cw, ch = 6, 28, 24; ent = [(k, st, s.c, s.ox, s.oy, 'solid' in s.tags) for k, sts in ns.items() for st, s in sts.items()]
from pixelart.vistas import nodes as fnodes
for k, (c, e, ox, oy) in {**M.nodes(), **fnodes()}.items(): ent += [(k, 'full', c, ox, oy, False), (k, 'depleted', e, ox, oy, False), (k, 'regrow', e, ox, oy, False)]
nsheet = Canvas(cols * cw, ((len(ent) + cols - 1) // cols) * ch); idx = {}
for i, (k, st, c, ox, oy, sol) in enumerate(ent):
    px, py = (i % cols) * cw, (i // cols) * ch; nsheet.blit(c, px, py); idx[f'{k}:{st}'] = dict(x=px, y=py, w=c.w, h=c.h, ox=ox, oy=oy, solid=sol)
Image.fromarray(nsheet.a, 'L').save(os.path.join(ROOT, 'assets/items/nodes_idx.png')); json.dump({'cell': [cw, ch], 'index': idx}, open(os.path.join(ROOT, 'assets/items/nodes_atlas.json'), 'w'))
T = lambda p: PAL.lut('spring', False) if not p else PAL.lut('spring', True)
names = ['wanderer_0', 'wanderer_1', 'stalker_0', 'stalker_1', 'stalker_crouch', 'burrower_0', 'burrower_1', 'burrower_2', 'burrower_3', 'howler_0', 'howler_call', 'brute_0', 'brute_swing', 'luminous_0', 'luminous_2']
for night, bg, tag in ((False, PAL.i('grass', 3), 'day'), (True, PAL.i('forest', 2), 'night')):
    W = sum(spr[n][0].w + 6 for n in names) + 8; can = Canvas(W, 70); can.rect(0, 0, W, 70, bg); X = 4
    for n in names: c = spr[n][0]; can.blit(c, X, 66 - c.h); X += c.w + 6
    Image.fromarray(can.to_rgba(T(night))).resize((W * 3, 210), Image.NEAREST).save(os.path.join(ROOT, f'renders/gallery_creatures_{tag}.png'))
print(len(spr), 'creature sprites;', len(ent), 'node sprites')
