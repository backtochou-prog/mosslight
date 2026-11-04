"""ORIGINAL player sprite v5: the happy survivor, built from parts.

22 x 38 px cells, feet on the bottom row (origin 11, 37). A cozy, chunky figure: a big round head under a soft felt hat,
a mustard field coat, a red scarf, denim, sturdy boots and a small pack with a bedroll. Warm peach skin, dark friendly eyes,
rosy cheeks and a smile, so it reads as a cheerful camper. Each part is drawn as a flat shape with a one-pixel highlight and
shade, outlined in warm ink, and stacked; every frame is composed from the same parts so the head and coat never jitter.
Walking is still exactly two images (foot up / standing), as asked.
"""
from __future__ import annotations
import json, os
import numpy as np
from .canvas import Canvas
from .palette import PAL

W, H = 22, 36
OX, OY = 11, 35
SRC_H, CUT = 38, (21, 23)        # drawn on a 38-row grid, then two rows are taken out of the middle of the torso: a compact, Stardew-height body
FACINGS = ['down', 'up', 'side', 'gather', 'fish', 'build', 'run_down', 'run_up', 'run_side', 'blink', 'hurt', 'sleep']
FRAMES = ['idle0', 'idle1', 'walk0', 'walk1', 'walk2', 'walk3']
IDLE_COLS, WALK_COLS, CONTACTS = [0, 1], [2, 3, 4, 5], [3, 5]
def r(f, k): return PAL.i(f, k)
INK = r('wood', 0)
SKIN = (r('shroom', 3), r('shroom', 3), r('dirt', 4))       # light, mid, shade
COAT = (r('flower_y', 1), r('flower_y', 0), r('leaf_litter', 1))
SHIRT = (r('flower_w', 1), r('rope', 2), r('rope', 1))
SCARF = (r('berry', 2), r('berry', 1), r('berry', 0))
DENIM = (r('flower_b', 2), r('flower_b', 1), r('flower_b', 0))
BOOT = (r('wood', 3), r('wood', 2), r('wood', 1))
HAT = (r('earth', 4), r('earth', 3), r('earth', 2))
HAIR = (r('wood', 3), r('wood', 2), r('wood', 1))
PACK = (r('reed', 2), r('reed', 1), r('reed', 0))
ROLL = (r('rope', 2), r('rope', 1), r('rope', 0))
EYE, WHITE, CHEEK, MOUTH = r('wood', 0), r('flower_w', 2), r('berry', 2), r('berry', 0)

def ell(cx, cy, rx, ry):
    m = np.zeros((SRC_H, W), bool)
    for y in range(SRC_H):
        for x in range(W):
            if ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 <= 1: m[y, x] = True
    return m
def box(x0, y0, x1, y1, round_=True):
    """inclusive rectangle with the four corners shaved for a soft, drawn look"""
    m = np.zeros((SRC_H, W), bool); m[y0:y1 + 1, x0:x1 + 1] = True
    if round_ and x1 - x0 > 3 and y1 - y0 > 3:
        for (x, y) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)): m[y, x] = False
    return m

class Fig:
    def __init__(self): self.c = Canvas(W, SRC_H)
    def part(self, m, col, outline=True, light=True, shade=True):
        """flat fill with a one-pixel highlight (top-left) and shade (bottom-right), outlined in ink"""
        if not m.any(): return
        t = Canvas(W, SRC_H); lt, mid, sh = col; t.a[m] = mid
        up = np.zeros_like(m); up[1:, 1:] = m[:-1, :-1]; dn = np.zeros_like(m); dn[:-1, :-1] = m[1:, 1:]
        if light: t.a[m & ~up] = lt
        if shade: t.a[m & ~dn] = sh
        if outline:
            e = np.zeros_like(m)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                s = np.roll(np.roll(m, dy, 0), dx, 1)
                if dy == 1: s[0, :] = False
                if dy == -1: s[-1, :] = False
                if dx == 1: s[:, 0] = False
                if dx == -1: s[:, -1] = False
                e |= s
            e &= ~m; self.c.a[e & (t.a == 0)] = INK
        self.c.a[m] = t.a[m]
    def px(self, pts, col):
        for x, y in pts:
            if 0 <= x < W and 0 <= y < SRC_H: self.c.a[y, x] = col

def shifted(f, dy):
    if not dy: return f
    o = Canvas(W, SRC_H); o.a[:SRC_H - dy] = f.a[dy:]; return o

# ---------------------------------------------------------------- front
VEST = (r('forest', 3), r('forest', 2), r('forest', 1))
STRAP = (r('wood', 5), r('wood', 4), r('wood', 2))
PANTS = (r('pebble', 2), r('pebble', 1), r('pebble', 0))
NECK = (r('flower_b', 2), r('flower_b', 1), r('flower_b', 0))
HAIRC = (r('leaf_litter', 2), r('wood', 3), r('wood', 2))      # warm auburn, light / mid / shade

def hair_front(f, b):
    f.part(ell(10.5, 7.2 - b, 6.9, 4.9), HAIRC)                                        # a full, tousled head of hair
    f.px([(7, 3 - b), (10, 2 - b), (13, 3 - b)], HAIRC[0])
def fringe(f, b, flip=False):
    f.part(ell(10.5, 8.6 - b, 5.6, 2.0), HAIRC, outline=False)                          # fringe over the brow
    f.px([(5, 10 - b), (5, 11 - b), (16, 10 - b), (16, 11 - b)], HAIRC[1])             # side locks

def torso_front(f, b):
    f.part(box(4, 17 - b, 17, 27 - b), SHIRT)                                          # shirt
    f.part(box(5, 17 - b, 7, 27 - b, False), VEST); f.part(box(14, 17 - b, 16, 27 - b, False), VEST)    # leather vest, open at the front
    f.c.line(6, 18 - b, 15, 26 - b, STRAP[1]); f.c.line(6, 17 - b, 15, 25 - b, STRAP[0])               # bandolier strap
    f.part(box(13, 23 - b, 16, 26 - b), VEST); f.px([(14, 24 - b)], STRAP[0])                           # hip pouch
    f.c.a[27 - b, 4:18] = BOOT[1]; f.px([(10, 27 - b), (11, 27 - b)], r('metal', 3))                    # belt, buckle
    f.part(box(8, 16 - b, 13, 18 - b), NECK)                                                         # neckerchief

def arms_front(f, b, hands):
    for x0, hy in ((1, hands[0]), (18, hands[1])):
        f.part(box(x0, 18 - b + hy, x0 + 2, 21 - b + hy), SHIRT)                       # sleeve, rolled
        f.part(box(x0, 22 - b + hy, x0 + 2, 25 - b + hy, False), SKIN); f.part(ell(x0 + 1.5, 26 - b + hy, 2, 2), SKIN)

def face_front(f, b, eyes):
    f.part(ell(5, 12 - b, 1.6, 2.6), SKIN, light=False); f.part(ell(16.2, 12 - b, 1.6, 2.6), SKIN, light=False)
    f.part(ell(10.5, 13 - b, 6.2, 5.6), SKIN)
    fringe(f, b)
    ey = 12 - b
    if eyes == 'open':
        for x in (7, 13): f.px([(x, ey), (x + 1, ey), (x, ey + 1), (x + 1, ey + 1)], EYE); f.px([(x, ey)], WHITE)
        f.px([(7, ey - 2), (8, ey - 2), (13, ey - 2), (14, ey - 2)], HAIRC[2])         # brows
    elif eyes == 'closed':
        for x in (7, 13): f.px([(x, ey + 1), (x + 1, ey + 1)], EYE)
        f.px([(7, ey - 2), (8, ey - 2), (13, ey - 2), (14, ey - 2)], HAIRC[2])
    elif eyes == 'hurt':
        for x in (7, 13): f.px([(x, ey), (x + 1, ey + 1)], EYE); f.px([(x + 1, ey), (x, ey + 1)], EYE)
        f.px([(7, ey - 2), (8, ey - 3), (13, ey - 3), (14, ey - 2)], HAIRC[2])
    f.px([(10, 13 - b)], SKIN[2])

def front(lift=None, hands=(0, 0), eyes='open', mouth='none', crouch=0, dy=0):
    f = Fig(); b = dy
    for side, x0 in (('L', 5), ('R', 12)):
        up = lift == side; ly = 27 - b
        if up:
            f.part(box(x0, ly, x0 + 4, ly + 4), PANTS)
            f.part(box(x0, ly + 5, x0 + 4, ly + 7), BOOT); f.px([(x0 + 1, ly + 7), (x0 + 2, ly + 7), (x0 + 3, ly + 7)], BOOT[2])
        else:
            f.part(box(x0, ly, x0 + 4, 34), PANTS); f.part(box(x0 - 1, 33, x0 + 5, 36), BOOT)
    f.px([(5, 36), (6, 36), (16, 36), (17, 36)], BOOT[2])
    arms_front(f, b, hands); torso_front(f, b)
    hair_front(f, b); face_front(f, b, eyes)
    if mouth == 'open': f.px([(10, 15 - b), (11, 15 - b), (10, 16 - b), (11, 16 - b)], MOUTH)
    return crouch_shift(f.c, crouch) if crouch else f.c

def crouch_shift(c, d):
    o = Canvas(W, SRC_H); o.a[d:SRC_H - 5] = c.a[:SRC_H - 5 - d]; o.a[SRC_H - 5:] = c.a[SRC_H - 5:]; return o

# ---------------------------------------------------------------- back
def back(lift=None, hands=(0, 0), dy=0):
    f = Fig(); b = dy
    for side, x0 in (('L', 5), ('R', 12)):
        up = lift == side; ly = 27 - b
        if up: f.part(box(x0, ly, x0 + 4, ly + 4), PANTS); f.part(box(x0, ly + 5, x0 + 4, ly + 7), BOOT)
        else: f.part(box(x0, ly, x0 + 4, 34), PANTS); f.part(box(x0 - 1, 33, x0 + 5, 36), BOOT)
    arms_front(f, b, hands)
    f.part(box(4, 17 - b, 17, 27 - b), SHIRT); f.part(box(5, 17 - b, 16, 27 - b, False), VEST)
    f.part(box(6, 15 - b, 15, 26 - b), PACK)                                           # pack
    f.px([(x, 21 - b) for x in range(7, 15)], PACK[2]); f.part(box(7, 22 - b, 14, 25 - b, False), PACK, outline=False); f.px([(10, 23 - b), (11, 23 - b)], r('flower_y', 2))
    f.part(box(5, 13 - b, 16, 16 - b), ROLL); f.px([(x, 14 - b) for x in range(6, 16, 3)], ROLL[2])      # bedroll
    f.part(ell(10.5, 11.5 - b, 6.2, 5.6), HAIRC)
    hair_front(f, b); f.part(ell(10.5, 12 - b, 6.2, 4.6), HAIRC, outline=False)
    f.px([(8, 4 - b), (12, 3 - b), (10, 6 - b)], HAIRC[0])
    return f.c

# ---------------------------------------------------------------- side (facing right; the engine flips for left)
def side(lift=False, arm='rest', eyes='open', mouth='none', dy=0, rod=None):
    f = Fig(); b = dy
    f.part(box(9, 27 - b, 12, 34), PANTS); f.part(box(8, 33, 14, 36), BOOT)
    f.part(box(4, 15 - b, 9, 26 - b), PACK); f.part(box(3, 13 - b, 10, 16 - b), ROLL); f.px([(5, 14 - b), (8, 14 - b)], ROLL[2]); f.px([(4, 20 - b), (4, 21 - b)], PACK[0])
    if lift:
        f.part(box(8, 27 - b, 16, 30 - b), PANTS); f.part(box(14, 30 - b, 17, 33 - b), PANTS); f.part(box(13, 33 - b, 19, 35 - b), BOOT)
    else:
        f.part(box(8, 27 - b, 13, 34), PANTS); f.part(box(7, 33, 14, 36), BOOT); f.px([(8, 36), (9, 36), (10, 36)], BOOT[2])
    f.part(box(6, 17 - b, 14, 27 - b), SHIRT); f.part(box(6, 17 - b, 13, 27 - b, False), VEST); f.c.line(6, 18 - b, 13, 25 - b, STRAP[1])
    f.c.a[26 - b, 6:15] = BOOT[1]
    f.part(box(8, 16 - b, 14, 18 - b), NECK)
    f.part(ell(10, 13 - b, 5.8, 5.6), SKIN)
    f.part(ell(8.4, 7.6 - b, 6.2, 5.0), HAIRC); f.part(ell(6.8, 11 - b, 3.0, 4.2), HAIRC, outline=False); f.px([(6, 2 - b), (9, 1 - b), (12, 2 - b)], HAIRC[0])
    f.part(ell(11.4, 8.6 - b, 4.0, 1.9), HAIRC, outline=False)                          # fringe
    f.part(box(15, 13 - b, 16, 14 - b, False), SKIN, shade=False)
    ey = 12 - b
    if eyes == 'open': f.px([(13, ey), (14, ey), (13, ey + 1), (14, ey + 1)], EYE); f.px([(13, ey)], WHITE); f.px([(13, ey - 2), (14, ey - 2)], HAIRC[2])
    elif eyes == 'closed': f.px([(13, ey + 1), (14, ey + 1)], EYE)
    elif eyes == 'hurt': f.px([(13, ey), (14, ey + 1), (14, ey), (13, ey + 1)], EYE)
    if mouth == 'open': f.px([(14, 15 - b), (14, 16 - b)], MOUTH)
    if arm == 'rest': f.part(box(8, 18 - b, 11, 21 - b), SHIRT); f.part(box(8, 22 - b, 11, 24 - b, False), SKIN); f.part(ell(10, 26 - b, 2, 2), SKIN)
    elif arm == 'back': f.part(box(6, 19 - b, 9, 22 - b), SHIRT); f.part(box(6, 23 - b, 9, 25 - b, False), SKIN); f.part(ell(7.5, 27 - b, 2, 2), SKIN)
    elif arm == 'fwd': f.part(box(11, 19 - b, 15, 22 - b), SHIRT); f.part(box(13, 22 - b, 16, 24 - b, False), SKIN); f.part(ell(16.5, 23.5 - b, 2, 2), SKIN)
    if rod: f.c.line(*rod[0], *rod[1], r('wood', 3)); f.c.put(*rod[1], r('wood', 4))
    return f.c

# ---------------------------------------------------------------- frames
def walk_frames(facing, run=False):
    """two images only: foot up, standing, foot up, standing; the lifted frame also swings the arms and rides a pixel higher"""
    if facing == 'down': up = front('L', hands=(-2, 1), dy=1); st = front('')
    elif facing == 'up': up = back('R', hands=(1, -2), dy=1); st = back()
    else: up = side(True, arm='back', dy=1); st = side()
    return [up, st, up, st]
def idle_frames(facing):
    base = {'down': front(), 'up': back(), 'side': side()}[facing]; return [base, base]

def action(kind, k):
    if kind == 'gather':
        c = front(crouch=[0, 1, 2, 2][k], hands=(0, [0, 2, 3, 3][k]), mouth='smile')
        if k == 3: c.put(20, 31, r('flower_y', 1)); c.put(19, 31, r('flower_y', 2))
        return c
    if kind == 'fish':
        tips = [(14, 8), (21, 2), (21, 4), (21, 6)][k]; return side(arm='fwd', rod=((16, 23), tips))
    if kind == 'build':
        c = front(hands=(0, -3 if k in (0, 1) else 0)); hy = [12, 9, 19, 24][k]
        c.line(20, 26, 20, hy + 2, r('wood', 2)); c.rect(19, hy, 3, 3, r('metal', 2)); c.put(19, hy, r('metal', 3)); return c

def sleep(k):
    f = Fig(); f.part(ell(11, 30, 10, 5), COAT); f.part(box(6, 24, 15, 27), ROLL)
    f.part(ell(5, 29, 3.2, 3.2), SKIN); f.part(ell(5, 27, 4, 2.4), HAIRC); f.px([(3, 30), (6, 30)], EYE); f.px([(4, 32 - k)], MOUTH)
    f.px([(17, 24 - 3 * k - 0)], r('flower_w', 2)); return f.c

def squash(c):
    a = c.a; o = Canvas(W, H); o.a[:] = np.concatenate([a[:CUT[0]], a[CUT[1]:]])[:H]; return o

def cell(facing, col):
    return squash(_cell(facing, col))

def _cell(facing, col):
    if facing in ('down', 'up', 'side'): return idle_frames(facing)[col] if col < 2 else walk_frames(facing)[col - 2]
    if facing.startswith('run_'):
        f = facing[4:]; return idle_frames(f)[col] if col < 2 else walk_frames(f, run=True)[col - 2]
    if facing in ('gather', 'fish', 'build'): return action(facing, col % 4)
    order = ['down', 'side', 'up']; f = order[col % 3]
    if facing == 'blink': return front(eyes='closed') if f == 'down' else side(eyes='closed') if f == 'side' else back()
    if facing == 'hurt': return front(eyes='hurt', mouth='open') if f == 'down' else side(eyes='hurt', mouth='open') if f == 'side' else back()
    if facing == 'sleep': return sleep(col % 2)

def build_sheet():
    sheet = Canvas(W * len(FRAMES), H * len(FACINGS))
    for fi, facing in enumerate(FACINGS):
        for ci in range(len(FRAMES)): sheet.blit(cell(facing, ci), ci * W, fi * H)
    meta = {'name': 'survivor v5 (original; cozy chunky camper, built from parts)', 'frame_w': W, 'frame_h': H, 'origin': [OX, OY],
            'facings': FACINGS, 'frames': FRAMES, 'rows': 'facing', 'cols': 'frame', 'side_flips_for_left': True,
            'idle_cols': IDLE_COLS, 'walk_cols': WALK_COLS, 'contacts': CONTACTS, 'walk_fps': 6, 'run_fps': 10, 'idle_fps': 1.0, 'foot_box': [9, 4],
            'action_frames': 4, 'action_fps': 6, 'shadow': [8, 2],
            'run': {'rows': {'down': 'run_down', 'up': 'run_up', 'side': 'run_side'}, 'cols': WALK_COLS},
            'blink': {'row': 'blink', 'cols': {'down': 0, 'side': 1, 'up': 2}, 'lifted_offset': 3},
            'hurt': {'row': 'hurt', 'cols': {'down': 0, 'side': 1, 'up': 2}},
            'sleep': {'row': 'sleep', 'cols': [0, 1], 'fps': 0.6}}
    return sheet, meta

def export(out_dir):
    sheet, meta = build_sheet(); os.makedirs(out_dir, exist_ok=True)
    from PIL import Image
    Image.fromarray(sheet.a, 'L').save(os.path.join(out_dir, 'player_idx.png')); sheet.save(os.path.join(out_dir, 'player_preview.png'), scale=1)
    json.dump(meta, open(os.path.join(out_dir, 'player.json'), 'w'), indent=1); return sheet, meta
