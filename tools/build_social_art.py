"""Atlases and an inspection gallery for the inhabitants."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image, ImageDraw
from pixelart.canvas import Canvas
from pixelart.palette import PAL
from pixelart import folk as F, fish as FP
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(ROOT, 'assets/social'); os.makedirs(OUT, exist_ok=True)
spr = {}
for k, (fn, n) in F.WORLD.items():
    for i in range(n): spr[f'{k}_{i}'] = fn(i)
AW = 256; x = y = rh = 0; pos = {}
for nm, (c, ox, oy) in sorted(spr.items(), key=lambda kv: -kv[1][0].h):
    if x + c.w > AW: x = 0; y += rh; rh = 0
    pos[nm] = dict(x=x, y=y, w=c.w, h=c.h, ox=ox, oy=oy); x += c.w; rh = max(rh, c.h)
sheet = Canvas(AW, y + rh)
for nm, (c, _, _) in spr.items(): sheet.blit(c, pos[nm]['x'], pos[nm]['y'])
Image.fromarray(sheet.a, 'L').save(os.path.join(OUT, 'folk_idx.png')); json.dump(dict(width=AW, index=pos), open(os.path.join(OUT, 'folk_atlas.json'), 'w'))
bgs = dict(ebb=['teal', 'aqua'], pip=['moss'], wick=['indigo'], burl=['olive'], tessel=['steel'], lull=['violet'])
por = {}
for k, fn in F.PORTRAITS.items():
    for e in F.EXPR:
        c = fn(e); por[f'{k}_{e}'] = c
names = list(por); ps = np.zeros((48 * len(F.PORTRAITS), 48 * 3), np.uint8); pidx = {}
for i, k in enumerate(F.PORTRAITS):
    for j, e in enumerate(F.EXPR): ps[i * 48:(i + 1) * 48, j * 48:(j + 1) * 48] = por[f'{k}_{e}'].a; pidx[f'{k}_{e}'] = [j * 48, i * 48]
Image.fromarray(ps, 'L').save(os.path.join(OUT, 'portraits_idx.png')); json.dump(dict(size=48, palette=FP.PALETTE, index=pidx), open(os.path.join(OUT, 'portraits.json'), 'w'))
# gallery: world sprites at 1x and 4x on grass by day and on forest floor at night, then portraits at 1x and 3x
lut_d, lut_n = PAL.lut('spring', False), PAL.lut('spring', True)
order = ['ebb', 'pip', 'wick', 'burl', 'tessel', 'lull']
G = Image.new('RGB', (1500, 980), (232, 222, 196)); d = ImageDraw.Draw(G)
for row, (lut, bg) in enumerate(((lut_d, PAL.i('grass', 3)), (lut_n, PAL.i('forest', 2)))):
    X = 10
    for k in order:
        for i in range(min(2, F.WORLD[k][1])):
            c, ox, oy = spr[f'{k}_{i}']; b = Canvas(c.w + 4, c.h + 4); b.rect(0, 0, b.w, b.h, bg); b.blit(c, 2, 2); im = Image.fromarray(b.to_rgba(lut)).convert('RGB').resize(((c.w + 4) * 3, (c.h + 4) * 3), Image.NEAREST)
            G.paste(im, (X, 10 + row * 170)); X += im.width + 4
    d.text((10, 160 + row * 170), 'day' if row == 0 else 'night', fill=(70, 50, 30))
pal = np.array(FP.PALETTE, np.uint8)
for i, k in enumerate(order):
    for j, e in enumerate(F.EXPR):
        a = por[f'{k}_{e}'].a; im = Image.fromarray(pal[a]).resize((144, 144), Image.NEAREST); G.paste(im, (10 + j * 150 + (i % 2) * 470, 360 + (i // 2) * 205))
        G.paste(Image.fromarray(pal[a]), (10 + j * 50 + (i % 2) * 470 + 0, 360 + (i // 2) * 205 + 148))
    d.text((10 + (i % 2) * 470 + 160, 360 + (i // 2) * 205 + 186), k, fill=(70, 50, 30))
G.save(os.path.join(ROOT, 'renders/folk_gallery.png')); print(len(spr), 'world frames', len(por), 'portraits')
