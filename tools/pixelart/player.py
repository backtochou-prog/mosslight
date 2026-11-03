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
FACINGS = ['down', 'up', 'side', 'gather', 'fish', 'build',
           'run_down', 'run_up', 'run_side', 'blink', 'hurt', 'sleep']   # new rows are APPENDED only
FRAMES = ['idle0', 'idle1', 'walk0', 'walk1', 'walk2', 'walk3']

def R(f): return PAL.ramp(f)

def _head(c, facing, y0, skin, skin_sh, hair, hair_lt, hair_dk, eye, white, mouth, eyes='open'):
    """12-wide head with a soft hair mass. y0 = top of hair.
    eyes: 'open' | 'closed' (blink: one dark lid line) | 'squeeze' (hurt: > < chevrons)."""
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
            _eye(c, ex, y0, eyes, eye, white, left=(ex == 5))
        if eyes == 'squeeze': c.hline(6, 9, y0 + 12, mouth)   # gritted wince
        else: c.hline(7, 8, y0 + 12, mouth)            # small mouth
        c.put(4, y0 + 10, skin_sh); c.put(11, y0 + 10, skin_sh)                   # cheeks
        c.hline(3, 12, y0 + 13, skin_sh)               # chin shade
    elif facing == 'side':
        _eye(c, 9, y0, eyes, eye, white, left=False)
        c.put(12, y0 + 9, skin_sh)                      # nose
        c.rect(hx0, y0 + 5, 5, 6, hair); c.put(hx0 + 4, y0 + 10, hair_dk)         # more hair toward the back
        c.hline(3, 12, y0 + 13, skin_sh)
    else:  # up: all hair, strands, a hint of ears
        c.rect(hx0, y0 + 1, 12, 12, hair); c.rect(hx0 + 1, y0, 10, 1, hair); c.put(hx0 + 5, y0 - 1, hair); c.put(hx0 + 6, y0 - 1, hair)
        c.hline(hx0 + 3, hx0 + 6, y0 + 1, hair_lt); c.put(hx0 + 2, y0 + 2, hair_lt)
        for x in (hx0 + 3, hx0 + 6, hx0 + 9): c.vline(x, y0 + 6, y0 + 11, hair_dk)
        c.hline(hx0 + 1, hx1 - 1, y0 + 12, hair_dk); c.put(hx0, y0 + 9, skin); c.put(hx1 - 1, y0 + 9, skin)

def _eye(c, ex, y0, mode, eye, white, left=True):
    if mode == 'open':
        c.rect(ex, y0 + 7, 2, 3, eye); c.put(ex, y0 + 7, white)
    elif mode == 'closed':                             # lid line on the lower row of the eye
        c.hline(ex, ex + 1, y0 + 9, eye)
    else:                                              # squeezed shut: > on the left eye, < on the right
        a, b = (ex, ex + 1) if left else (ex + 1, ex)
        c.put(a, y0 + 7, eye); c.put(b, y0 + 8, eye); c.put(a, y0 + 9, eye)

def draw_frame(facing: str, frame: str) -> Canvas:
    if facing in ('gather', 'fish', 'build'):
        return draw_action(facing, int(frame[-1]) % 4)
    if facing.startswith('run_'):
        return draw_run(facing[4:], frame)
    if facing == 'blink':
        return draw_blink(frame)
    if facing == 'hurt':
        return draw_hurt(frame)
    if facing == 'sleep':
        return draw_sleep(frame)
    return _figure(facing, frame)

def _figure(facing: str, frame: str, run=False, eyes='open', hurt=False) -> Canvas:
    """The standing figure. Defaults reproduce the original down/up/side rows pixel for pixel.
    run: longer stride, lean, pumping arms, trailing hair/scarf, body lifted on the strides.
    hurt: flinch (head tucked, shoulders up, arms guarding)."""
    c = Canvas(W, H)
    cv, fern, dirt, wood, berry, fw, moss = R('canvas'), R('fern'), R('dirt'), R('wood'), R('berry'), R('flower_w'), R('moss')
    skin, skin_sh = cv[5], cv[3]
    hair, hair_lt, hair_dk = wood[2], wood[3], wood[1]
    jacket, jacket_lt, jacket_sh = fern[2], fern[3], fern[1]
    eye, white, mouth = wood[0], fw[2], cv[2]
    bob = 0
    walk = frame.startswith('walk')
    k = int(frame[-1]) if walk else 0
    run = run and walk
    lift = frame in ('walk0', 'walk2') if run else frame in ('idle1', 'walk1', 'walk3')
    stride = {0: (-1, 1), 1: (0, 0), 2: (1, -1), 3: (0, 0)}[k] if walk and not run else (0, 0)
    y0 = 1 + bob                                          # hair top
    by = y0 + 14                                          # body top
    ly = by + 9                                           # legs top (= 24 + bob)
    hdx, hdy = 0, 0                                       # head offset: run lean / hurt tuck
    post = []                                             # (x, y, idx) painted after the outline (thin tips that must keep their colour)
    if run: hdx, hdy = (1, 0) if facing == 'side' else (0, 1)
    if hurt: hdx, hdy = (-1, 1) if facing == 'side' else (0, 1)
    head = Canvas(W, H)
    _head(head, facing, y0, skin, skin_sh, hair, hair_lt, hair_dk, eye, white, mouth, eyes=eyes)
    if run and facing != 'side' and k % 2 == 1:           # tuft sways on the pass frames
        head.put(7, y0 - 1, 0); head.put(9, y0 - 1, hair)
    if facing == 'side':
        # body: narrower, one arm in front
        c.rect(4, by, 8, 9, jacket); c.rect(4, by, 2, 9, jacket_lt); c.rect(10, by, 2, 9, jacket_sh)
        c.hline(5, 10, by, berry[1]); c.put(6, by + 1, berry[0])                       # scarf
        if run:
            if k == 0:   c.rect(6, by + 2, 2, 3, jacket_sh); c.rect(5, by + 5, 2, 1, jacket_sh); c.put(4, by + 6, skin_sh)   # near arm back
            elif k == 2: c.rect(9, by + 2, 2, 3, jacket_sh); c.rect(11, by + 3, 1, 2, jacket_sh); c.put(12, by + 2, skin_sh)  # near arm pumped forward
            else:        c.rect(8, by + 2, 2, 4, jacket_sh); c.put(9, by + 6, skin_sh)                                     # bent, passing
        elif not hurt:
            ax = 8 + (stride[0] if walk else 0)
            c.rect(ax, by + 2, 2, 5, jacket_sh); c.put(ax, by + 7, skin_sh)             # arm
        c.put(4, by + 3, moss[1]); c.put(4, by + 4, moss[1])                            # pack strap edge
        if run:
            far, near = dirt[1], dirt[2]
            def leg(x, col, boot, pose):
                if pose == 'plant': c.rect(x, ly, 3, 5, col); c.rect(x, ly + 5, 3, 2, boot)
                elif pose == 'fwd': c.rect(x + 1, ly, 3, 3, col); c.rect(x + 2, ly + 2, 3, 3, col); c.rect(x + 2, ly + 5, 4, 2, boot)
                elif pose == 'back': c.rect(x - 1, ly, 3, 2, col); c.rect(x - 2, ly + 1, 3, 2, col); c.rect(x - 3, ly + 3, 3, 2, boot)
                else: c.rect(x, ly, 3, 3, col); c.rect(x - 1, ly + 3, 3, 2, boot)          # tuck: passing leg lifted
            fp, np_ = {0: ('back', 'fwd'), 1: ('tuck', 'plant'), 2: ('fwd', 'back'), 3: ('plant', 'tuck')}[k]
            hip = {'fwd': 6, 'back': 6, 'plant': 7, 'tuck': 5}                            # strides mirror about x = 7
            leg(hip[fp], far, wood[0], fp); leg(hip[np_], near, wood[1], np_)
        else:
            # legs: 2 legs of 3 px, alternate forward/back
            lf, lb = stride
            c.rect(5 + lb, ly, 3, 5, dirt[1]); c.rect(8 + lf, ly, 3, 5, dirt[2])
            c.rect(5 + lb, ly + 5, 3, 2 - bob, wood[0]); c.rect(8 + lf, ly + 5, 3, 2 - bob, wood[1])
        c.blit(head, hdx, hdy)
        if run:                                                                         # hair and scarf stream behind
            c.vline(2, y0 + 5 + k % 2, y0 + 8 + k % 2, hair); c.put(2, y0 + 5 + k % 2, hair_dk)
            post += [(3, by, berry[1]), (2, by + (k % 2), berry[0])]                     # scarf tail, kept in colour past the outline
        if hurt:
            c.hline(4, 10, by + 1, berry[1])                                            # scarf shows below the tucked chin
            c.rect(8, by + 2, 2, 3, jacket_sh); c.put(9, by + 1, skin_sh); c.put(10, by + 1, skin_sh)   # arm drawn up, fist clutching the scarf
    else:
        c.rect(3, by, 10, 9, jacket); c.rect(3, by, 3, 9, jacket_lt); c.rect(11, by, 2, 9, jacket_sh)
        if facing == 'down':
            c.hline(5, 10, by, berry[1]); c.put(10, by + 1, berry[0]); c.put(5, by + 1, berry[1])   # scarf
            c.vline(8, by + 2, by + 8, jacket_sh)                                             # seam
            c.put(4, by + 2, moss[1]); c.put(11, by + 2, moss[1])                             # strap tops
        else:
            c.rect(5, by + 1, 6, 6, cv[2]); c.hline(5, 10, by + 1, cv[3]); c.put(5, by + 1, cv[1])  # backpack
            c.hline(5, 10, by + 7, cv[1])
        if run:
            # pumping arms: one raised and bent, one swung back low; neutral-bent on the pass frames
            up_l = {0: False, 1: None, 2: True, 3: None}[k]
            for ax in (2, 13):
                col = jacket_lt if ax == 2 else jacket_sh
                raised = None if up_l is None else (up_l == (ax == 2))
                if raised is None: c.rect(ax, by + 1, 1, 5, col); c.put(ax, by + 6, skin_sh)
                elif raised:       c.rect(ax, by, 1, 4, col); c.put(ax + (1 if ax == 2 else -1), by + 4, skin_sh)
                else:              c.rect(ax, by + 2, 1, 6, col); c.put(ax, by + 8, skin_sh)
            # legs: forward leg reaches a row lower (toward the viewer), the other kicks up
            def leg(x, col, boot, pose):
                if pose == 'fwd':    c.rect(x, ly, 3, 6, col); c.rect(x, ly + 6, 3, 2, boot)
                elif pose == 'back': c.rect(x, ly, 3, 3, col); c.rect(x, ly + 3, 3, 2, boot)
                elif pose == 'tuck': c.rect(x, ly, 3, 4, col); c.rect(x, ly + 4, 3, 2, boot)
                else:                c.rect(x, ly, 3, 5, col); c.rect(x, ly + 5, 3, 2, boot)
            lp, rp = {0: ('fwd', 'back'), 1: ('plant', 'tuck'), 2: ('back', 'fwd'), 3: ('tuck', 'plant')}[k]
            leg(4, dirt[1], wood[0], lp); leg(9, dirt[2], wood[1], rp)
        elif hurt:
            for ax in (2, 13):                                                             # shoulders hunched, arms drawn in
                col = jacket_lt if ax == 2 else jacket_sh
                c.rect(ax, by - 1, 1, 5, col)
            if facing == 'down': c.put(4, by + 4, skin_sh); c.put(11, by + 4, skin_sh)    # fists at the chest
            c.rect(4, ly, 3, 5, dirt[1]); c.rect(9, ly, 3, 5, dirt[2])
            c.rect(4, ly + 5, 3, 2, wood[0]); c.rect(9, ly + 5, 3, 2, wood[1])
        else:
            for (ax, sw) in ((2, stride[0]), (13, stride[1])):                                   # arms swing
                ay = by + 1 + (sw if walk else 0)
                c.rect(ax, ay, 1, 6, jacket_lt if ax == 2 else jacket_sh); c.put(ax, ay + 6, skin_sh)
            lf, lb = stride
            c.rect(4, ly + max(0, -lf), 3, 5 - max(0, -lf), dirt[1]); c.rect(9, ly + max(0, -lb), 3, 5 - max(0, -lb), dirt[2])
            c.rect(4, ly + 5, 3, 2 - bob, wood[0]); c.rect(9, ly + 5, 3, 2 - bob, wood[1])
        c.blit(head, hdx, hdy)
        if hdy and facing == 'down':                                                       # scarf re-shown under the lowered chin
            c.hline(5, 10, by + 1, berry[1]); c.put(10, by + 2, berry[0]); c.put(5, by + 2, berry[1])
        if run and facing == 'down':                                                       # scarf knot end flaps
            c.put(10 + (k % 2), by + 2, berry[0])
        if run and facing == 'up':                                                         # scarf tail streams back over the pack
            x = 7 if k % 2 == 0 else 8
            c.put(x, by, berry[1]); c.put(x, by + 1, berry[1]); c.put(x + (-1 if k % 2 == 0 else 1), by + 2, berry[0])
    if lift:                                            # chest and head rise one row, legs stay planted
        a = c.a.copy(); c.a[0:ly - 1, :] = a[1:ly, :]; c.a[ly - 1, :] = a[ly - 1, :]
    c.outline_inside(wood[0])
    for (x, y, idx) in post:
        c.put(x, y - 1 if (lift and y < ly) else y, idx)
    return c

def draw_run(facing: str, frame: str) -> Canvas:
    """run_down / run_up / run_side. Walk columns hold the 4-frame run; idle columns copy the idle pose."""
    return _figure(facing, frame, run=True)

BLINK_COLS = {'idle0': ('down', 'idle0'), 'idle1': ('side', 'idle0'), 'walk0': ('up', 'idle0'),
              'walk1': ('down', 'idle1'), 'walk2': ('side', 'idle1'), 'walk3': ('up', 'idle1')}
HURT_COLS = {'idle0': 'down', 'idle1': 'side', 'walk0': 'up', 'walk1': 'down', 'walk2': 'side', 'walk3': 'up'}

def draw_blink(frame: str) -> Canvas:
    """Eyes-closed twin of an idle frame (walk1..3 = the breath-lifted idle1 versions)."""
    facing, f = BLINK_COLS[frame]
    return _figure(facing, f, eyes='open' if facing == 'up' else 'closed')

def draw_hurt(frame: str) -> Canvas:
    facing = HURT_COLS[frame]
    return _figure(facing, 'idle0', eyes='open' if facing == 'up' else 'squeeze', hurt=True)

def draw_sleep(frame: str) -> Canvas:
    """Lying face-up in a bedroll, seen from above; the figure fills the lower 16 px of the cell.
    idle0/walk0/walk2 = rest, idle1/walk1/walk3 = breath (the roll's fold rises one row)."""
    c = Canvas(W, H)
    cv, dirt, wood, berry = R('canvas'), R('dirt'), R('wood'), R('berry')
    skin, skin_sh = cv[5], cv[3]
    hair, hair_lt, hair_dk = wood[2], wood[3], wood[1]
    breath = frame in ('idle1', 'walk1', 'walk3')
    t = 16                                                # top of the lower half
    # bedroll: hood around the head, body below; lit left edge, shaded right edge
    c.rect(1, t + 3, 14, 29 - t, dirt[2]); c.rect(0, t + 5, 16, 25 - t, dirt[2])
    c.rect(1, t + 4, 2, 27 - t, dirt[3]); c.rect(13, t + 4, 2, 27 - t, dirt[1])
    # head, face up: rounded hair cap, scalloped fringe, closed eyes, tiny mouth
    c.rect(4, t, 8, 1, hair); c.rect(3, t + 1, 10, 1, hair); c.rect(2, t + 2, 12, 2, hair)
    c.hline(5, 8, t + 1, hair_lt); c.put(4, t + 2, hair_lt)
    c.rect(3, t + 4, 10, 4, skin); c.rect(4, t + 8, 8, 1, skin)
    c.rect(2, t + 4, 1, 3, hair); c.rect(13, t + 4, 1, 3, hair)
    for i, x in enumerate(range(3, 13)):
        c.put(x, t + 4, hair_dk if i % 3 != 1 else hair)
    for ex in (5, 9): c.hline(ex, ex + 1, t + 6, wood[0])                             # closed eyes
    c.put(4, t + 7, skin_sh); c.put(11, t + 7, skin_sh); c.put(7, t + 8, cv[2])
    # turned-down liner at the chin; the fold rises a row on the in-breath
    ry = t + 9 - (1 if breath else 0)
    c.hline(2, 13, ry, cv[4]); c.hline(2, 13, ry + 1, cv[3]); c.put(2, ry, cv[3]); c.put(13, ry, cv[3])
    c.put(4, ry + 1, skin_sh); c.put(5, ry + 1, skin_sh)                              # a hand over the fold
    c.put(11, ry + 2, berry[1]); c.put(11, ry + 3, berry[0])                          # scarf end tucked in
    c.hline(3, 12, 29, dirt[1]); c.hline(4, 11, 30, dirt[1])                          # roll seam, feet end in shade
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
            'actions': {'gather': 'row 3, 4 frames', 'fish': 'row 4, 4 frames, side facing', 'build': 'row 5, 4 frames'}, 'action_fps': 6,
            'run': {'rows': {'down': 'run_down', 'up': 'run_up', 'side': 'run_side'}, 'frames': ['walk0', 'walk1', 'walk2', 'walk3'],
                    'fps': 12, 'note': 'idle0/idle1 of run rows copy the idle pose'},
            'blink': {'row': 'blink', 'down': 'idle0', 'side': 'idle1', 'up': 'walk0',
                      'lifted': {'down': 'walk1', 'side': 'walk2', 'up': 'walk3'},
                      'note': 'eyes-closed twins of idle0 (and of breath-lifted idle1 via lifted); hold ~0.12 s'},
            'hurt': {'row': 'hurt', 'down': 'idle0', 'side': 'idle1', 'up': 'walk0', 'note': 'flinch pose; walk1..3 copy idle0/idle1/walk0'},
            'sleep': {'row': 'sleep', 'frames': ['idle0', 'idle1'], 'fps': 0.6, 'note': 'lying in a bedroll seen from above, lower 16 px of the cell; walk0..3 alternate copies'}}
    return sheet, meta

def export(out_dir):
    sheet, meta = build_sheet()
    os.makedirs(out_dir, exist_ok=True)
    from PIL import Image
    Image.fromarray(sheet.a, 'L').save(os.path.join(out_dir, 'player_idx.png'))
    sheet.save(os.path.join(out_dir, 'player_preview.png'), scale=1)
    json.dump(meta, open(os.path.join(out_dir, 'player.json'), 'w'), indent=1)
    return sheet, meta
