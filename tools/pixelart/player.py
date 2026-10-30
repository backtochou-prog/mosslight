"""ORIGINAL player sprite ("the camper"), cozy-sim proportions.

16 x 32 px, origin at the feet (8, 31). Chibi proportions: head (hair + face)
is ~14 px of the 32, a compact 9-px body, short 6-px legs with 2-px boots.
Three facings (down, up, side; side flips for left), idle x2 (breath),
walk x4 (left stride, pass, right stride, pass) plus action rows
(gather, fish, build). Palette families only: canvas (skin), wood (hair,
boots, outline), fern/shrub (jacket), dirt (trousers), berry (scarf accent),
flower_w (eye whites), moss (pack strap).
"""
from __future__ import annotations
import json, os
import numpy as np
from .canvas import Canvas
from .palette import PAL

W, H = 16, 32
OX, OY = 8, 31
FACINGS = ['down', 'up', 'side', 'gather', 'fish', 'build']
FRAMES = ['idle0', 'idle1', 'walk0', 'walk1', 'walk2', 'walk3']

def R(f): return PAL.ramp(f)

def _head(c, facing, y0, skin, skin_sh, hair, hair_lt, hair_dk, eye, white, mouth):
    """12-wide head with a soft hair mass. y0 = top of hair."""
    hx0, hx1 = 2, 13
    # face block (rows y0+4 .. y0+13), hair cap on top and down the sides
    c.rect(hx0 + 1, y0 + 3, 10, 11, skin)
    c.rect(hx0, y0 + 1, 12, 4, hair); c.rect(hx0 + 1, y0, 10, 1, hair)      # rounded cap
    c.put(hx0 + 5, y0 - 1, hair); c.put(hx0 + 6, y0 - 1, hair)              # a tuft on top
    c.rect(hx0, y0 + 5, 2, 5, hair); c.rect(hx1 - 1, y0 + 5, 2, 4, hair)     # sides
    c.put(hx0 + 1, y0 + 10, hair_dk); c.put(hx1 - 1, y0 + 9, hair_dk)
    c.hline(hx0 + 3, hx0 + 6, y0 + 1, hair_lt); c.put(hx0 + 2, y0 + 2, hair_lt)    # shine
    for i, x in enumerate(range(hx0 + 1, hx1)):                               # scalloped fringe
        c.put(x, y0 + 4, hair_dk if i % 3 != 1 else hair)
        if i % 3 == 0: c.put(x, y0 + 5, hair)
    if facing == 'down':
        for ex in (5, 9):                              # big simple eyes: 2 wide, 3 tall
            c.rect(ex, y0 + 7, 2, 3, eye); c.put(ex, y0 + 7, white)
        c.hline(7, 8, y0 + 12, mouth)                  # small mouth
        c.put(4, y0 + 10, skin_sh); c.put(11, y0 + 10, skin_sh)                   # cheeks
        c.hline(3, 12, y0 + 13, skin_sh)               # chin shade
    elif facing == 'side':
        c.rect(9, y0 + 7, 2, 3, eye); c.put(9, y0 + 7, white)
        c.put(12, y0 + 9, skin_sh)                      # nose
        c.rect(hx0, y0 + 5, 5, 6, hair); c.put(hx0 + 4, y0 + 10, hair_dk)         # more hair toward the back
        c.hline(3, 12, y0 + 13, skin_sh)
    else:  # up: all hair, strands, a hint of ears
        c.rect(hx0, y0 + 1, 12, 12, hair); c.rect(hx0 + 1, y0, 10, 1, hair); c.put(hx0 + 5, y0 - 1, hair); c.put(hx0 + 6, y0 - 1, hair)
        c.hline(hx0 + 3, hx0 + 6, y0 + 1, hair_lt); c.put(hx0 + 2, y0 + 2, hair_lt)
        for x in (hx0 + 3, hx0 + 6, hx0 + 9): c.vline(x, y0 + 6, y0 + 11, hair_dk)
        c.hline(hx0 + 1, hx1 - 1, y0 + 12, hair_dk); c.put(hx0, y0 + 9, skin); c.put(hx1 - 1, y0 + 9, skin)

def draw_frame(facing: str, frame: str) -> Canvas:
    if facing in ('gather', 'fish', 'build'):
        return draw_action(facing, int(frame[-1]) % 4)
    c = Canvas(W, H)
    cv, fern, dirt, wood, berry, fw, moss = R('canvas'), R('fern'), R('dirt'), R('wood'), R('berry'), R('flower_w'), R('moss')
    skin, skin_sh = cv[5], cv[3]
    hair, hair_lt, hair_dk = wood[2], wood[3], wood[1]
    jacket, jacket_lt, jacket_sh = fern[2], fern[3], fern[1]
    eye, white, mouth = wood[0], fw[2], cv[2]
    bob = 0
    lift = frame in ('idle1', 'walk1', 'walk3')
    walk = frame.startswith('walk')
    k = int(frame[-1]) if walk else 0
    stride = {0: (-1, 1), 1: (0, 0), 2: (1, -1), 3: (0, 0)}[k] if walk else (0, 0)
    y0 = 1 + bob                                          # hair top
    by = y0 + 14                                          # body top
    ly = by + 9                                           # legs top (= 24 + bob)
    if facing == 'side':
        # body: narrower, one arm in front
        c.rect(4, by, 8, 9, jacket); c.rect(4, by, 2, 9, jacket_lt); c.rect(10, by, 2, 9, jacket_sh)
        c.hline(5, 10, by, berry[1]); c.put(6, by + 1, berry[0])                       # scarf
        ax = 8 + (stride[0] if walk else 0)
        c.rect(ax, by + 2, 2, 5, jacket_sh); c.put(ax, by + 7, skin_sh)                 # arm
        c.put(4, by + 3, moss[1]); c.put(4, by + 4, moss[1])                            # pack strap edge
        # legs: 2 legs of 3 px, alternate forward/back
        lf, lb = stride
        c.rect(5 + lb, ly, 3, 5, dirt[1]); c.rect(8 + lf, ly, 3, 5, dirt[2])
        c.rect(5 + lb, ly + 5, 3, 2 - bob, wood[0]); c.rect(8 + lf, ly + 5, 3, 2 - bob, wood[1])
        _head(c, 'side', y0, skin, skin_sh, hair, hair_lt, hair_dk, eye, white, mouth)
    else:
        c.rect(3, by, 10, 9, jacket); c.rect(3, by, 3, 9, jacket_lt); c.rect(11, by, 2, 9, jacket_sh)
        if facing == 'down':
            c.hline(5, 10, by, berry[1]); c.put(10, by + 1, berry[0]); c.put(5, by + 1, berry[1])   # scarf
            c.vline(8, by + 2, by + 8, jacket_sh)                                             # seam
            c.put(4, by + 2, moss[1]); c.put(11, by + 2, moss[1])                             # strap tops
        else:
            c.rect(5, by + 1, 6, 6, cv[2]); c.hline(5, 10, by + 1, cv[3]); c.put(5, by + 1, cv[1])  # backpack
            c.hline(5, 10, by + 7, cv[1])
        for (ax, sw) in ((2, stride[0]), (13, stride[1])):                                   # arms swing
            ay = by + 1 + (sw if walk else 0)
            c.rect(ax, ay, 1, 6, jacket_lt if ax == 2 else jacket_sh); c.put(ax, ay + 6, skin_sh)
        lf, lb = stride
        c.rect(4, ly + max(0, -lf), 3, 5 - max(0, -lf), dirt[1]); c.rect(9, ly + max(0, -lb), 3, 5 - max(0, -lb), dirt[2])
        c.rect(4, ly + 5, 3, 2 - bob, wood[0]); c.rect(9, ly + 5, 3, 2 - bob, wood[1])
        _head(c, facing, y0, skin, skin_sh, hair, hair_lt, hair_dk, eye, white, mouth)
    if lift:                                            # chest and head rise one row, legs stay planted
        a = c.a.copy(); c.a[0:ly - 1, :] = a[1:ly, :]; c.a[ly - 1, :] = a[ly - 1, :]
    c.outline_inside(wood[0])
    return c

def draw_action(action: str, k: int) -> Canvas:
    base = 'side' if action == 'fish' else 'down'
    c = draw_frame(base, 'idle0')
    wood, cv, mt = R('wood'), R('canvas'), R('metal')
    if action == 'gather':
        if k in (1, 2):                                  # bend: whole figure drops 2 px, a hand reaches the ground
            a = c.a.copy(); c.a[:, :] = 0; c.a[2:, :] = a[:-2, :]; c.a[30:, :] = 0
            c.rect(4, 29, 3, 2, wood[0]); c.rect(9, 29, 3, 2, wood[1]); c.put(2, 27, cv[3]); c.put(2, 28, cv[3])
        if k == 3: c.put(2, 20, R('flower_y')[1])
    elif action == 'fish':
        rod = [(11, 18, 15, 10), (11, 17, 15, 8), (11, 18, 15, 9), (11, 18, 15, 11)][k]
        c.line(rod[0], rod[1], rod[2], rod[3], wood[3]); c.put(rod[2], rod[3], wood[4])
        if k in (2, 3): c.vline(15, rod[3] + 1, min(31, rod[3] + 6 + k), cv[5])
    elif action == 'build':
        hy = [12, 10, 15, 18][k]
        c.rect(13, hy, 2, 2, mt[2]); c.put(14, hy + 2, wood[2]); c.put(14, hy + 3, wood[2])
    return c

def build_sheet():
    sheet = Canvas(W * len(FRAMES), H * len(FACINGS))
    for fi, facing in enumerate(FACINGS):
        for ki, frame in enumerate(FRAMES):
            fr = draw_action(facing, ki % 4) if facing in ('gather', 'fish', 'build') else draw_frame(facing, frame)
            sheet.blit(fr, ki * W, fi * H)
    meta = {'name': 'camper (original player sprite, cozy-sim proportions)', 'frame_w': W, 'frame_h': H, 'origin': [OX, OY],
            'facings': FACINGS, 'frames': FRAMES, 'rows': 'facing', 'cols': 'frame', 'side_flips_for_left': True,
            'walk_fps': 8, 'idle_fps': 1.5, 'foot_box': [8, 4],
            'actions': {'gather': 'row 3, 4 frames', 'fish': 'row 4, 4 frames, side facing', 'build': 'row 5, 4 frames'}, 'action_fps': 6}
    return sheet, meta

def export(out_dir):
    sheet, meta = build_sheet()
    os.makedirs(out_dir, exist_ok=True)
    from PIL import Image
    Image.fromarray(sheet.a, 'L').save(os.path.join(out_dir, 'player_idx.png'))
    sheet.save(os.path.join(out_dir, 'player_preview.png'), scale=1)
    json.dump(meta, open(os.path.join(out_dir, 'player.json'), 'w'), indent=1)
    return sheet, meta
