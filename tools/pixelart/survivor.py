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
def front(lift=None, hands=(0, 0), eyes='open', mouth='smile', crouch=0, dy=0):
    """lift: 'L' or 'R' raises that boot (knee up, sole showing); hands: vertical offset of (left, right) hand; dy: whole body up"""
    f = Fig(); b = dy
    # legs and boots
    for side, x0 in (('L', 5), ('R', 12)):
        up = lift == side; ly = 26 - b
        if up:
            f.part(box(x0, ly, x0 + 4, ly + 3), DENIM)                              # thigh, knee toward you
            f.part(box(x0, ly + 4, x0 + 4, ly + 6), BOOT); f.px([(x0 + 1, ly + 6), (x0 + 2, ly + 6), (x0 + 3, ly + 6)], BOOT[2])   # sole
        else:
            f.part(box(x0, ly, x0 + 4, 33), DENIM); f.part(box(x0 - 1, 33, x0 + 5, 36), BOOT)
    f.px([(5, 36), (6, 36), (16, 36), (17, 36)], BOOT[2])
    # backpack straps peeking at the shoulders are drawn with the coat
    f.part(box(4, 17 - b, 17, 27 - b), COAT)                                           # coat
    f.part(box(9, 18 - b, 12, 24 - b, False), SHIRT, outline=False)                    # shirt in the open front
    f.px([(10, 18 - b), (11, 18 - b)], SHIRT[2]); f.c.a[25 - b, 4:18] = BOOT[1]; f.px([(10, 25 - b), (11, 25 - b)], r('flower_y', 2))   # belt, buckle
    f.px([(5, y) for y in range(18 - b, 25 - b)], COAT[0]); f.px([(7, 20 - b), (7, 21 - b), (14, 20 - b), (14, 21 - b)], COAT[2])       # coat folds
    f.px([(6, 17 - b), (6, 18 - b), (15, 17 - b), (15, 18 - b)], PACK[1])             # pack straps
    f.part(box(7, 16 - b, 14, 18 - b), SCARF)                                          # scarf
    f.part(box(13, 18 - b, 15, 21 - b), SCARF)                                         # scarf tail
    # arms (a little out from the body, hands relaxed)
    for side, x0, hy in (('L', 1, hands[0]), ('R', 18, hands[1])):
        f.part(box(x0, 18 - b + hy, x0 + 2, 24 - b + hy), COAT); f.part(ell(x0 + 1.5, 26 - b + hy, 2, 2), SKIN)
    # head
    f.part(ell(5, 12 - b, 1.6, 2.6), SKIN, light=False); f.part(ell(16.2, 12 - b, 1.6, 2.6), SKIN, light=False)               # ears
    f.part(ell(10.5, 12.5 - b, 6.4, 5.4), SKIN)
    f.part(ell(10.5, 8 - b, 6.2, 3), HAIR, outline=False)                              # fringe
    f.px([(4, 13 - b), (4, 14 - b), (17, 13 - b), (17, 14 - b)], HAIR[1])
    ey = 12 - b
    if eyes == 'open':
        for x in (7, 13): f.px([(x, ey), (x + 1, ey), (x, ey + 1), (x + 1, ey + 1)], EYE); f.px([(x, ey)], WHITE)
    elif eyes == 'closed':
        for x in (7, 13): f.px([(x, ey + 1), (x + 1, ey + 1)], EYE)
    elif eyes == 'hurt':
        for x in (7, 13): f.px([(x, ey), (x + 1, ey + 1)], EYE); f.px([(x + 1, ey), (x, ey + 1)], EYE)
    f.px([(10, 13 - b)], SKIN[2])
    if mouth == 'open': f.px([(10, 15 - b), (11, 15 - b), (10, 16 - b), (11, 16 - b)], MOUTH)
    # hat: wide soft brim, rounded crown, red band
    f.part(ell(10.5, 7.2 - b, 9.6, 2.7), HAT)
    f.part(box(5, 1 - b, 16, 6 - b), HAT); f.c.a[5 - b, 6:16] = r('berry', 1); f.c.a[4 - b, 6:16] = r('berry', 2)
    f.px([(7, 2 - b), (8, 2 - b), (9, 1 - b)], HAT[0])
    return shifted(f.c, 0) if not crouch else crouch_shift(f.c, crouch)

def crouch_shift(c, d):
    o = Canvas(W, SRC_H); o.a[d:SRC_H - 5] = c.a[:SRC_H - 5 - d]; o.a[SRC_H - 5:] = c.a[SRC_H - 5:]; return o

# ---------------------------------------------------------------- back
def back(lift=None, hands=(0, 0), dy=0):
    f = Fig(); b = dy
    for side, x0 in (('L', 5), ('R', 12)):
        up = lift == side; ly = 26 - b
        if up:
            f.part(box(x0, ly, x0 + 4, ly + 3), DENIM); f.part(box(x0, ly + 4, x0 + 4, ly + 6), BOOT)
        else:
            f.part(box(x0, ly, x0 + 4, 33), DENIM); f.part(box(x0 - 1, 33, x0 + 5, 36), BOOT)
    for side, x0, hy in (('L', 1, hands[0]), ('R', 18, hands[1])):
        f.part(box(x0, 18 - b + hy, x0 + 2, 24 - b + hy), COAT); f.part(ell(x0 + 1.5, 26 - b + hy, 2, 2), SKIN)
    f.part(box(4, 17 - b, 17, 27 - b), COAT)
    f.part(box(6, 15 - b, 15, 26 - b), PACK)                                           # pack
    f.px([(x, 22 - b) for x in range(7, 15)], PACK[2]); f.part(box(7, 23 - b, 14, 25 - b, False), PACK, outline=False); f.px([(10, 25 - b), (11, 25 - b)], r('flower_y', 2))
    f.part(box(5, 13 - b, 16, 16 - b), ROLL); f.px([(x, 14 - b) for x in range(6, 16, 3)], ROLL[2])      # bedroll
    f.px([(8, 26 - b), (13, 26 - b)], r('metal', 3))
    f.part(ell(10.5, 11.5 - b, 6.4, 5.4), HAIR)
    f.part(ell(10.5, 7.2 - b, 9.6, 2.7), HAT); f.part(box(5, 1 - b, 16, 6 - b), HAT); f.c.a[5 - b, 6:16] = r('berry', 1); f.c.a[4 - b, 6:16] = r('berry', 2)
    f.px([(7, 2 - b), (8, 2 - b), (9, 1 - b)], HAT[0])
    return f.c

# ---------------------------------------------------------------- side (facing right; the engine flips for left)
def side(lift=False, arm='rest', eyes='open', mouth='smile', dy=0, rod=None):
    f = Fig(); b = dy
    # far leg first, behind
    f.part(box(9, 26 - b, 12, 33), DENIM); f.part(box(8, 33, 14, 36), BOOT)
    f.part(box(4, 15 - b, 9, 25 - b), PACK); f.part(box(3, 13 - b, 10, 16 - b), ROLL); f.px([(5, 14 - b), (8, 14 - b)], ROLL[2]); f.px([(4, 20 - b), (4, 21 - b)], PACK[0])
    # near leg
    if lift:
        f.part(box(8, 26 - b, 16, 31 - b), DENIM); f.part(box(14, 31 - b, 17, 33 - b), DENIM); f.part(box(13, 33 - b, 19, 35 - b), BOOT)
    else:
        f.part(box(8, 26 - b, 13, 33), DENIM); f.part(box(7, 33, 14, 36), BOOT); f.px([(8, 36), (9, 36), (10, 36)], BOOT[2])
    f.part(box(6, 17 - b, 14, 27 - b), COAT); f.px([(7, y) for y in range(18 - b, 24 - b)], COAT[0]); f.c.a[25 - b, 6:15] = BOOT[1]
    f.part(box(8, 16 - b, 14, 18 - b), SCARF); f.part(box(5, 17 - b, 7, 21 - b), SCARF)
    # head, facing right
    f.part(ell(10, 12.5 - b, 5.6, 5.4), SKIN); f.part(ell(7.4, 11.5 - b, 2.8, 4.6), HAIR, outline=False)
    f.part(box(15, 13 - b, 16, 14 - b, False), SKIN, shade=False)                       # nose
    ey = 12 - b
    if eyes == 'open': f.px([(13, ey), (14, ey), (13, ey + 1), (14, ey + 1)], EYE); f.px([(13, ey)], WHITE)
    elif eyes == 'closed': f.px([(13, ey + 1), (14, ey + 1)], EYE)
    elif eyes == 'hurt': f.px([(13, ey), (14, ey + 1), (14, ey), (13, ey + 1)], EYE)
    if mouth == 'open': f.px([(14, 15 - b), (14, 16 - b)], MOUTH)
    f.part(ell(11, 7.2 - b, 9.6, 2.7), HAT); f.part(box(6, 1 - b, 16, 6 - b), HAT); f.c.a[5 - b, 7:16] = r('berry', 1); f.c.a[4 - b, 7:16] = r('berry', 2); f.px([(8, 2 - b), (9, 2 - b), (10, 1 - b)], HAT[0])
    # near arm
    if arm == 'rest': f.part(box(8, 18 - b, 11, 24 - b), COAT); f.part(ell(10, 26 - b, 2, 2), SKIN)
    elif arm == 'back': f.part(box(6, 19 - b, 9, 25 - b), COAT); f.part(ell(7.5, 27 - b, 2, 2), SKIN)
    elif arm == 'fwd': f.part(box(11, 19 - b, 15, 23 - b), COAT); f.part(ell(16, 23.5 - b, 2, 2), SKIN)
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
    f.part(ell(5, 29, 3.2, 3.2), SKIN); f.part(ell(5, 27, 4, 2.2), HAT); f.px([(3, 30), (6, 30)], EYE); f.px([(4, 32 - k)], MOUTH)
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
