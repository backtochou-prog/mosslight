"""Atlas + preview for construction art: assets/build/{build_idx.png, build_atlas.json}."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
from pixelart.canvas import Canvas
from pixelart.palette import PAL
from pixelart import building as B
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(ROOT, 'assets/build'); os.makedirs(OUT, exist_ok=True)
spr = B.all_sprites(); AW = 640; x = y = rh = 0; items = sorted(spr.items(), key=lambda kv: -kv[1][0].h); pos = {}
for nm, (c, ox, oy) in items:
    if x + c.w > AW: x = 0; y += rh; rh = 0
    pos[nm] = dict(x=x, y=y, w=c.w, h=c.h, ox=ox, oy=oy); x += c.w; rh = max(rh, c.h)
sheet = Canvas(AW, y + rh)
for nm, (c, _, _) in items: sheet.blit(c, pos[nm]['x'], pos[nm]['y'])
Image.fromarray(sheet.a, 'L').save(os.path.join(OUT, 'build_idx.png')); json.dump({'width': AW, 'index': pos}, open(os.path.join(OUT, 'build_atlas.json'), 'w'))
print(len(spr), 'construction sprites, atlas', AW, y + rh)
# ---- preview: a small house composed by hand, plus every furniture sprite
W, H = 26, 13; T = 16; can = Canvas(W * T, H * T); can.rect(0, 0, can.w, can.h, PAL.i('grass', 3))
cells = {(x, y) for x in range(2, 9) for y in range(5, 11)}
def blit(nm, x, y): c, ox, oy = spr[nm]; can.blit(c, x - ox, y - oy)
for (cx, cy) in sorted(cells):
    m = (2 if (cx + 1, cy) in cells else 0) | (4 if (cx, cy + 1) in cells else 0) | (8 if (cx - 1, cy) in cells else 0); blit(f'fnd_wood_{m}', cx * T, cy * T)
inner = {(x, y) for x in range(3, 8) for y in range(6, 10)}
for c_ in inner: blit('floor_plank', c_[0] * T, c_[1] * T)
walls = {c_ for c_ in cells if c_ not in inner}
for (cx, cy) in sorted(walls, key=lambda c: c[1]):
    m = sum(b for b, d in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))) if (cx + d[0], cy + d[1]) in walls)
    nm = f'wall_cottage_{m}'
    if (cx, cy) == (5, 10): nm = 'door_closed_cottage'
    if (cx, cy) in ((3, 10), (7, 10)): nm = 'window_cottage'
    blit(nm, cx * T, cy * T + 11)
for (nm, x_, y_) in (('bed_cottage', 76, 130), ('table_rustic', 112, 130), ('rug_woven', 90, 150)): blit(nm, x_, y_)
# same house roofed, to the right
dx = 8 * T
cells2 = {(x + 8, y) for x, y in cells}; walls2 = {(x + 8, y) for x, y in walls}
for (cx, cy) in sorted(cells2):
    m = (2 if (cx + 1, cy) in cells2 else 0) | (4 if (cx, cy + 1) in cells2 else 0) | (8 if (cx - 1, cy) in cells2 else 0); blit(f'fnd_stone_{m}', cx * T, cy * T)
for (cx, cy) in sorted(walls2, key=lambda c: c[1]):
    m = sum(b for b, d in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))) if (cx + d[0], cy + d[1]) in walls2)
    nm = f'wall_stone_{m}'
    if (cx, cy) == (13, 10): nm = 'door_closed_reinforced'
    if (cx, cy) == (11, 10): nm = 'window_stone'
    blit(nm, cx * T, cy * T + 11)
for (cx, cy) in sorted(cells2):
    i = cy - 5; n = 6; ridge = 2; part = 'eave' if i == n - 1 else ('ridge' if i == ridge else ('north' if i < ridge else 'south'))
    blit(f'roof_shingle_{part}_{int(cx == 10)}{int(cx == 16)}', cx * T, cy * T - 34)
x_ = 18 * T; y_ = 32
for k in B.furniture():
    c = spr[k][0]
    if x_ + c.w > can.w - 2: x_ = 18 * T; y_ += 50
    blit(k, x_ + spr[k][1], y_ + spr[k][2]); x_ += c.w + 3
Image.fromarray(can.to_rgba(PAL.day), 'RGBA').resize((can.w * 3, can.h * 3), Image.NEAREST).save(os.path.join(ROOT, 'renders/check_construction_preview_3x.png'))
