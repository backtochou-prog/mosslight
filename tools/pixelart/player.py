"""TEMPORARY original player sprite ("the camper"), in the house pixel language.

14 x 24 px, origin at the feet (7, 23). Three facings (down, up, side; side is
flipped for left). Frames: idle x2 (breath), walk x4. Palette families only:
canvas (skin/pack), fern (jacket), dirt (trousers), wood (hair/boots/outline),
berry (scarf accent). Marked temporary in docs: a character artist should
replace it; origin, size and frame layout are the contract.
"""
from __future__ import annotations
import json, os
import numpy as np
from .canvas import Canvas
from .palette import PAL

W, H = 14, 24
OX, OY = 7, 23
FACINGS = ['down', 'up', 'side', 'gather', 'fish', 'build']
FRAMES = ['idle0', 'idle1', 'walk0', 'walk1', 'walk2', 'walk3']

def R(f): return PAL.ramp(f)

def draw_action(action: str, k: int) -> Canvas:
    """Action rows reuse the body: gather = facing down, bending to the ground;
    fish = side, rod out over the water; build = down, hammer swing."""
    base = 'side' if action == 'fish' else 'down'
    c = draw_frame(base, 'idle0')
    wood, cv, mt = R('wood'), R('canvas'), R('metal')
    if action == 'gather':
        # bend: shift head/body down on frames 1-2, hand reaches the ground
        if k in (1, 2):
            a = c.a.copy(); c.a[:, :] = 0; c.a[2:, :] = a[:-2, :]; c.a[22:, :] = 0
            c.rect(3, 20, 3, 2, wood[0]); c.rect(8, 20, 3, 2, wood[1])
            c.put(1, 19, cv[3]); c.put(1, 20, cv[3])
        if k == 3: c.put(1, 14, R('flower_y')[1])                      # something picked
    elif action == 'fish':
        rod = [(10, 9, 13, 3), (10, 8, 13, 1), (10, 9, 13, 2), (10, 9, 13, 4)][k]
        c.line(rod[0], rod[1], rod[2], rod[3], wood[3]); c.put(rod[2], rod[3], wood[4])
        if k in (2, 3): c.vline(13, rod[3] + 1, rod[3] + 5 + k, cv[5])   # line down to the water
    elif action == 'build':
        hy = [6, 4, 8, 10][k]
        c.rect(11, hy, 2, 2, mt[2]); c.put(12, hy + 2, wood[2]); c.put(12, hy + 3, wood[2])
    return c

def draw_frame(facing: str, frame: str) -> Canvas:
    if facing in ('gather', 'fish', 'build'):
        k = int(frame[-1]) if frame.startswith('walk') else int(frame[-1])
        return draw_action(facing, min(3, k if frame.startswith('idle') else k))
    c = Canvas(W, H)
    cv, fern, dirt, wood, berry = R('canvas'), R('fern'), R('dirt'), R('wood'), R('berry')
    skin, skin_sh = cv[4], cv[3]
    hair, hair_lt = wood[1], wood[2]
    jacket, jacket_lt, jacket_sh = fern[2], fern[3], fern[1]
    bob = 1 if frame in ('idle1', 'walk1', 'walk3') else 0
    walk = frame.startswith('walk')
    k = int(frame[-1]) if walk else 0
    # legs: alternate forward/back on walk frames (frames 0/2 = stride, 1/3 = pass)
    stride = {0: (-1, 1), 1: (0, 0), 2: (1, -1), 3: (0, 0)}[k] if walk else (0, 0)
    y0 = 2 + bob
    if facing == 'side':
        # ---- body (narrower), facing right
        c.rect(4, y0 + 8, 7, 8, jacket); c.rect(4, y0 + 8, 2, 8, jacket_lt); c.rect(9, y0 + 8, 2, 8, jacket_sh)
        c.hline(5, 9, y0 + 8, berry[1])                              # scarf
        # arm swings
        ax = 7 + (stride[0] if walk else 0)
        c.rect(ax, y0 + 10, 2, 5, jacket_sh); c.put(ax, y0 + 15, skin_sh)
        # head
        c.rect(4, y0, 7, 7, skin); c.rect(4, y0, 7, 3, hair); c.rect(4, y0 + 3, 2, 3, hair); c.put(10, y0 + 1, hair_lt)
        c.put(9, y0 + 4, wood[0])                                     # eye
        c.put(10, y0 + 5, skin_sh)                                    # nose
        # legs
        lf, lb = stride
        c.rect(5 + lb, y0 + 16, 2, 4, dirt[1]); c.rect(8 + lf, y0 + 16, 2, 4, dirt[2])
        c.rect(5 + lb, y0 + 20, 2, 2 - bob, wood[0]); c.rect(8 + lf, y0 + 20, 2, 2 - bob, wood[1])
    else:
        # ---- body
        c.rect(2, y0 + 8, 10, 8, jacket); c.rect(2, y0 + 8, 3, 8, jacket_lt); c.rect(10, y0 + 8, 2, 8, jacket_sh)
        if facing == 'down':
            c.hline(4, 9, y0 + 8, berry[1]); c.put(9, y0 + 9, berry[0])     # scarf
            c.vline(7, y0 + 10, y0 + 15, jacket_sh)                          # jacket seam
        else:
            c.rect(4, y0 + 9, 6, 6, cv[2]); c.rect(4, y0 + 9, 6, 1, cv[3]); c.put(4, y0 + 9, cv[1])   # backpack
        # arms
        for (ax, sw) in ((1, stride[0]), (12, stride[1])):
            ay = y0 + 9 + (sw if walk else 0)
            c.rect(ax, ay, 1, 6, jacket_sh if ax == 12 else jacket_lt); c.put(ax, ay + 6, skin_sh)
        # head
        c.rect(3, y0, 8, 7, skin); c.rect(3, y0, 8, 3, hair)
        if facing == 'down':
            c.put(3, y0 + 3, hair); c.put(10, y0 + 3, hair); c.put(4, y0 + 1, hair_lt); c.put(5, y0 + 1, hair_lt)
            c.put(5, y0 + 4, wood[0]); c.put(8, y0 + 4, wood[0])                # eyes
            c.put(6, y0 + 6, skin_sh); c.put(7, y0 + 6, skin_sh)                # chin shade
        else:
            c.rect(3, y0, 8, 6, hair); c.put(4, y0 + 1, hair_lt); c.put(5, y0 + 1, hair_lt); c.hline(3, 10, y0 + 6, skin_sh)
        # legs
        lf, lb = stride
        c.rect(3, y0 + 16 + max(0, -lf), 3, 4 - max(0, -lf), dirt[1]); c.rect(8, y0 + 16 + max(0, -lb), 3, 4 - max(0, -lb), dirt[2])
        c.rect(3, y0 + 20, 3, 2 - bob, wood[0]); c.rect(8, y0 + 20, 3, 2 - bob, wood[1])
    c.outline_inside(wood[0])
    return c

def build_sheet():
    sheet = Canvas(W * len(FRAMES), H * len(FACINGS))
    for fi, facing in enumerate(FACINGS):
        for ki, frame in enumerate(FRAMES):
            if facing in ('gather', 'fish', 'build'):
                fr = draw_action(facing, ki % 4)
            else:
                fr = draw_frame(facing, frame)
            sheet.blit(fr, ki * W, fi * H)
    meta = {'name': 'camper (TEMPORARY original player sprite)', 'frame_w': W, 'frame_h': H, 'origin': [OX, OY],
            'facings': FACINGS, 'frames': FRAMES, 'rows': 'facing', 'cols': 'frame', 'side_flips_for_left': True,
            'walk_fps': 8, 'idle_fps': 1.5, 'foot_box': [8, 4], 'actions': {'gather': 'row 3, 4 frames (cols 0-3)', 'fish': 'row 4, 4 frames, side facing', 'build': 'row 5, 4 frames'}, 'action_fps': 6}
    return sheet, meta

def export(out_dir):
    sheet, meta = build_sheet()
    os.makedirs(out_dir, exist_ok=True)
    from PIL import Image
    Image.fromarray(sheet.a, 'L').save(os.path.join(out_dir, 'player_idx.png'))
    sheet.save(os.path.join(out_dir, 'player_preview.png'), scale=1)
    json.dump(meta, open(os.path.join(out_dir, 'player.json'), 'w'), indent=1)
    return sheet, meta
