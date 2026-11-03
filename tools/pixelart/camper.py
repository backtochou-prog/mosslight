"""ORIGINAL player sprite v3: "the camper", cozy proportions, jointed motion.

24 x 36 px cells, feet at (12, 34). Visible figure is about 31 px tall (two tiles), so it stays in scale with
the camp. Proportions are soft and cozy: a big round head (~40% of the height), a chunky knitted
sweater over a little belly, short legs in brown trousers, sturdy boots, a red scarf with a loose tail and a
canvas backpack. Nothing here is traced or adapted from any other game.

How it moves: limbs are jointed (thigh, shin, upper arm, forearm) and posed per frame from gait tables, so a
step has contact, down, passing and up poses; the body bobs and leans; hair, scarf tail and backpack follow a
frame behind (secondary motion). Walk and run are 8 frames, idles breathe over 4.

Sheet layout (rows x 12 columns):
  rows: down, up, side, gather, fish, build, run_down, run_up, run_side, blink, hurt, sleep
  cols: idle0..idle3, walk0..walk7   (action rows use cols 0..5; blink/hurt use cols 0..2 = down, side, up,
        and blink cols 3..5 are the same on the raised breath frame; sleep uses cols 0..1)
"""
from __future__ import annotations
import json, math, os
import numpy as np
from .canvas import Canvas
from .palette import PAL

W, H = 24, 36
OX, OY = 12, 34
FACINGS = ['down', 'up', 'side', 'gather', 'fish', 'build', 'run_down', 'run_up', 'run_side', 'blink', 'hurt', 'sleep']
FRAMES = ['idle0', 'idle1', 'idle2', 'idle3'] + [f'walk{k}' for k in range(8)]
IDLE_COLS, WALK_COLS = [0, 1, 2, 3], list(range(4, 12))
CONTACTS = [4, 8]                     # footstep columns (walk0, walk4)

def R(f): return PAL.ramp(f)
SKIN = R('canvas'); HAIR = R('leaf_litter'); KNIT = R('flower_b'); TROU = R('dirt'); BOOT = R('wood'); SCARF = R('berry')
PACK = R('rope'); WHITE = R('flower_w'); STONE = R('stone'); FY = R('flower_y'); MT = R('metal')
INK = BOOT[0]                          # the warm dark outline

# ---------------------------------------------------------------- tiny raster helpers
def limb(c, x0, y0, ang, length, width, col, shade=None):
    """a rounded limb segment from (x0, y0) at angle ang (radians, 0 = straight down, + = toward +x); returns its end"""
    x1, y1 = x0 + math.sin(ang) * length, y0 + math.cos(ang) * length
    steps = max(2, int(length * 3))
    for s in range(steps + 1):
        t = s / steps; cx, cy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        for dy in range(-width, width + 1):
            for dx in range(-width, width + 1):
                if dx * dx + dy * dy <= width * width * .6 + .4:
                    c.put(int(round(cx + dx * .5)), int(round(cy + dy * .5)), col)
    if shade is not None:                                      # a shade along the trailing edge
        nx, ny = math.cos(ang), -math.sin(ang)
        for s in range(steps + 1):
            t = s / steps; cx, cy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            c.put(int(round(cx - nx * width * .5)), int(round(cy - ny * width * .5)), shade)
    return x1, y1

def disc(c, cx, cy, rx, ry, col):
    for y in range(int(cy - ry - 1), int(cy + ry + 2)):
        for x in range(int(cx - rx - 1), int(cx + rx + 2)):
            if ((x - cx) / (rx + .3)) ** 2 + ((y - cy) / (ry + .3)) ** 2 <= 1: c.put(x, y, col)

def fam_dark(idx, steps=1):
    """the same material, darker"""
    f = PAL.family_of(idx); r = PAL.rank_of(idx)
    if f is None or r is None: return INK
    return PAL.i(f, max(0, r - steps))

def outline(c):
    """outer silhouette line in warm ink; where two parts meet inside, the lower part's edge darkens"""
    a = c.a; m = a > 0; h, w = a.shape; out = a.copy()
    for y in range(h):
        for x in range(w):
            if m[y, x]: continue
            if any(0 <= y + dy < h and 0 <= x + dx < w and m[y + dy, x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))): out[y, x] = INK
    c.a[:] = out

# ---------------------------------------------------------------- parts
def head(c, facing, cx, top, eyes='open', hair_lag=0, mouth='smile'):
    """a big soft head: 14 wide, 13 tall, hair with volume, fringe and side locks; cx = centre column, top = first row"""
    cy = top + 7
    disc(c, cx, cy, 6.4, 6.2, SKIN[4])                                     # face and skull
    disc(c, cx - .6, cy + .9, 5.0, 4.8, SKIN[5]) if facing != 'up' else None   # lit cheek plane
    if facing == 'down':
        for y in range(top, top + 7):                                      # hair mass: a round crown over the face
            for x in range(cx - 7, cx + 8):
                d = ((x - cx + .5) / 7.4) ** 2 + ((y - (top + 6.2)) / 6.2) ** 2
                if d <= 1: c.put(x, y, HAIR[2])
        CLUMP = {-6: 2, -5: 3, -4: 3, -3: 2, -2: 1, -1: 2, 0: 3, 1: 3, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2}   # three soft clumps, parted to one side
        for x in range(cx - 6, cx + 7):
            b = top + 4 + CLUMP[x - cx]
            for y in range(top + 4, b): c.put(x, y, HAIR[2])
            if CLUMP[x - cx] >= 3: c.put(x, b - 1, HAIR[1])
        for s, x in ((-1, cx - 7), (1, cx + 7)):                           # side locks, which sway a frame behind
            for y in range(top + 5, top + 11 + (1 if s < 0 else 0)): c.put(x + (hair_lag if y > top + 8 else 0) * s * 0, y, HAIR[2])
            c.put(x - s, top + 11, HAIR[1])
        c.put(cx + 7 + (1 if hair_lag > 0 else 0), top + 10, HAIR[1])
        for x in range(cx - 4, cx + 1): c.put(x, top + 2, HAIR[3])          # shine
        c.put(cx - 5, top + 3, HAIR[3]); c.put(cx + 2, top + 1, HAIR[3])
        c.put(cx + 2, top - 1 + (1 if hair_lag else 0), HAIR[2])          # one stray hair that bounces
        # eyes: tall ovals with a light catch; brows from the fringe
        for ex in (cx - 3, cx + 2):
            if eyes == 'open':
                c.rect(ex, top + 8, 2, 3, BOOT[0]); c.put(ex + (1 if ex < cx else 0), top + 8, WHITE[2]); c.put(ex, top + 10, BOOT[1])
            elif eyes == 'closed': c.hline(ex, ex + 1, top + 10, BOOT[0]); c.put(ex - (1 if ex < cx else -2), top + 10, SKIN[3])
            else: c.put(ex + (0 if ex < cx else 1), top + 8, BOOT[0]); c.put(ex + (1 if ex < cx else 0), top + 9, BOOT[0]); c.put(ex + (0 if ex < cx else 1), top + 10, BOOT[0])
        c.put(cx - 5, top + 11, SCARF[2]); c.put(cx + 4, top + 11, SCARF[2])  # warm cheeks
        if mouth == 'smile': c.put(cx - 1, top + 12, SKIN[2]); c.put(cx, top + 12, SKIN[2]); c.put(cx - 2, top + 11, SKIN[3])
        elif mouth == 'wince': c.hline(cx - 2, cx + 1, top + 12, SKIN[1])
        c.hline(cx - 4, cx + 3, top + 13, SKIN[3])                          # chin into shadow
        c.put(cx - 7, top + 9, SKIN[3]); c.put(cx + 6, top + 9, SKIN[3])   # ears
    elif facing == 'side':                                                 # profile, looking toward +x
        for y in range(top, top + 13):
            for x in range(cx - 8, cx + 6):
                d = ((x - (cx - 1)) / 6.6) ** 2 + ((y - (top + 6)) / 6.4) ** 2
                if d <= 1 and not (x > cx + 1 and y > top + 5) and not (x >= cx - 1 and y > top + 8): c.put(x, y, HAIR[2])
        for y in range(top + 6, top + 12): c.put(cx - 7 - (1 if hair_lag and y > top + 8 else 0), y, HAIR[2])   # hair at the nape trails a little
        c.put(cx - 6, top + 12, HAIR[1])
        for x in range(cx - 1, cx + 5): c.put(x, top + 5 + (1 if x > cx + 2 else 0), HAIR[1])   # fringe edge
        for x in range(cx - 5, cx - 1): c.put(x, top + 2, HAIR[3])
        c.put(cx - 2, top - 1 + (1 if hair_lag else 0), HAIR[2])
        c.put(cx + 7, top + 9, SKIN[4]); c.put(cx + 7, top + 10, SKIN[3])   # nose
        if eyes == 'open': c.rect(cx + 3, top + 8, 2, 3, BOOT[0]); c.put(cx + 4, top + 8, WHITE[2])
        elif eyes == 'closed': c.hline(cx + 3, cx + 4, top + 10, BOOT[0])
        else: c.put(cx + 3, top + 8, BOOT[0]); c.put(cx + 4, top + 9, BOOT[0]); c.put(cx + 3, top + 10, BOOT[0])
        c.put(cx + 3, top + 11, SCARF[2])
        c.put(cx, top + 9, SKIN[3]); c.put(cx, top + 10, SKIN[3]); c.put(cx - 1, top + 10, HAIR[1])   # ear, tucked under the hair
        c.put(cx + 5, top + 12, SKIN[2] if mouth != 'wince' else SKIN[1])
        c.hline(cx - 2, cx + 4, top + 13, SKIN[3])
    else:                                                                  # from behind: all hair, a parting, the ears
        for y in range(top + 1, top + 13):
            for x in range(cx - 7, cx + 8):
                d = ((x - cx) / 7.0) ** 2 + ((y - (top + 6.5)) / 6.6) ** 2
                if d <= 1: c.put(x, y, HAIR[2])
        for x in range(cx - 5, cx + 6): c.put(x, top + 12, HAIR[1])
        for y in range(top + 3, top + 11, 2): c.put(cx - 3, y, HAIR[1]); c.put(cx + 3, y + 1, HAIR[1])
        for x in range(cx - 3, cx + 2): c.put(x, top + 2, HAIR[3])
        c.put(cx - 7, top + 9, SKIN[3]); c.put(cx + 7, top + 9, SKIN[3])
        c.put(cx + (1 if hair_lag else 0), top - 1, HAIR[2]); c.put(cx - 1, top + 13, HAIR[1]); c.put(cx + 1, top + 13, HAIR[1])

def torso(c, facing, cx, top, breath=0, scarf_lag=0, pack_lag=0):
    """the knitted sweater (rounded, a little belly), ribbed hem, scarf, backpack and straps; top = shoulder row"""
    bot = top + 10
    if facing == 'side':
        # backpack behind (toward -x), bobbing a frame late
        py = top + 1 + pack_lag
        for y in range(py, py + 7):
            for x in range(cx - 7, cx - 2):
                if not ((y in (py, py + 6)) and x in (cx - 7,)): c.put(x, y, PACK[1])
        for y in range(py + 1, py + 6): c.put(cx - 7, y, PACK[0])
        c.hline(cx - 6, cx - 4, py, PACK[2]); c.hline(cx - 6, cx - 3, py + 3, PACK[0]); c.put(cx - 5, py + 4, FY[1])
        for y in range(top, bot):                                           # sweater, narrower in profile, belly to the front
            for x in range(cx - 3, cx + 4 + (1 if top + 4 <= y <= top + 8 else 0)): c.put(x, y, KNIT[1])
            c.put(cx + 3 + (1 if top + 4 <= y <= top + 8 else 0), y, KNIT[0])
        for y in range(top, top + 4): c.put(cx - 2, y, KNIT[2])
        for x in range(cx - 3, cx + 4): c.put(x, bot - 1, KNIT[0] if x % 2 else KNIT[1])   # rib
        for x in range(cx - 3, cx + 4): c.put(x, top, SCARF[1]); c.put(x, top + 1, SCARF[1] if x < cx + 3 else SCARF[0])
        c.put(cx - 2, top + 2, SCARF[0])
        for y in range(top + 2, top + 6): c.put(cx - 3 - scarf_lag - (1 if y > top + 3 else 0), y, SCARF[1])   # tail flies back
        c.put(cx - 1, top + 2, PACK[0]); c.put(cx - 1, top + 3, PACK[0])  # strap
        return
    # front or back
    for y in range(top, bot):
        half = 4 if y == top else (5.5 if y == top + 1 else 6 if y < top + 3 else 6.5 if y < top + 8 else 6)
        for x in range(int(cx - half), int(cx + half) + (0 if half == int(half) else 1)):
            c.put(x, y, KNIT[1])
    for y in range(top + 1, bot - 1): c.put(cx - 6, y, KNIT[2])               # light from the left
    c.put(cx - 5, top + 1, KNIT[2]); c.put(cx - 4, top, KNIT[2])
    for y in range(top + 2, bot - 1): c.put(cx + 5 + (1 if top + 3 <= y < top + 8 else 0), y, KNIT[0])
    for x in range(cx - 6, cx + 6): c.put(x, bot - 1, KNIT[0] if x % 2 == 0 else KNIT[1]); c.put(x, bot - 2, KNIT[1] if x % 2 == 0 else KNIT[0] if facing == 'up' else KNIT[1])
    if facing == 'down':
        for y in range(top + 3, bot - 2, 2): c.put(cx - 2, y, KNIT[0]); c.put(cx + 2, y + 1, KNIT[0])   # cable knit
        for x in range(cx - 5, cx + 5): c.put(x, top, SCARF[1]); c.put(x, top + 1, SCARF[1] if x > cx - 5 else SCARF[2])
        c.hline(cx - 4, cx + 3, top, SCARF[2]); c.put(cx + 2, top + 1, SCARF[0])
        for y in range(top + 2, top + 6): c.put(cx + 2 + (scarf_lag if y > top + 3 else 0), y, SCARF[1]); c.put(cx + 3 + (scarf_lag if y > top + 3 else 0), y, SCARF[0] if y < top + 5 else SCARF[1])
        for y in range(top + 1, top + 5): c.put(cx - 4, y, PACK[1]); c.put(cx + 4, y, PACK[1])   # straps over the shoulders
    else:
        py = top + 1 + pack_lag                                             # backpack seen from behind
        for y in range(py, py + 8):
            for x in range(cx - 4, cx + 5):
                if not (y in (py, py + 7) and x in (cx - 4, cx + 4)): c.put(x, y, PACK[1])
        c.hline(cx - 3, cx + 3, py, PACK[2]); c.hline(cx - 4, cx + 4, py + 3, PACK[0]); c.rect(cx - 1, py + 4, 3, 2, PACK[2]); c.put(cx, py + 4, FY[1])
        for x in range(cx - 5, cx + 5): c.put(x, top, SCARF[1])

def boot(c, x, y, facing, front=True, toe=0):
    """a sturdy boot whose sole sits on row y"""
    col, lt = (BOOT[2], BOOT[3]) if front else (BOOT[1], BOOT[2])
    if facing == 'side':
        c.rect(x - 1, y - 2, 4 + toe, 3, col); c.hline(x - 1, x + 2 + toe, y, BOOT[0]); c.hline(x, x + 1, y - 2, lt)
    else:
        c.rect(x - 2, y - 2, 4, 3, col); c.hline(x - 2, x + 1, y, BOOT[0]); c.put(x - 1, y - 2, lt)

def arm_front(c, x, y, swing, side, raised=0):
    """front/back view: a sleeve hanging from the shoulder; swing moves the hand forward (up and in) by a pixel"""
    hx = x + (0 if abs(swing) < .5 else (-side if swing > 0 else 0)); hy = y + 7 - (1 if swing > .5 else 0) - raised
    for yy in range(y + 1, hy): c.put(x, yy, KNIT[0]); c.put(x + side, yy, KNIT[1] if side > 0 else KNIT[2])
    c.put(x + side, y, KNIT[1]); c.put(x + side, hy - 1, KNIT[0]); c.put(x, hy - 1, KNIT[0])
    c.rect(min(hx, hx + side), hy, 2, 2, SKIN[4]); c.put(hx + (side if side > 0 else 0), hy + 1, SKIN[3])

# ---------------------------------------------------------------- gait tables (radians; + = forward)
D = math.radians
WALK = [  # (near thigh, near knee, far thigh, far knee, arm swing, bob)
    (D(26), D(4), D(-22), D(18), -1.0, 0), (D(16), D(14), D(-24), D(34), -.6, 1), (D(2), D(6), D(-8), D(58), 0, 0), (D(-14), D(2), D(18), D(30), .6, -1),
    (D(-22), D(18), D(26), D(4), 1.0, 0), (D(-24), D(34), D(16), D(14), .6, 1), (D(-8), D(58), D(2), D(6), 0, 0), (D(18), D(30), D(-14), D(2), -.6, -1)]
RUN = [
    (D(40), D(10), D(-38), D(50), -1, 0), (D(28), D(30), D(-44), D(80), -1, 1), (D(6), D(40), D(-20), D(100), 0, -1), (D(-20), D(20), D(30), D(70), 1, -2),
    (D(-38), D(50), D(40), D(10), 1, 0), (D(-44), D(80), D(28), D(30), 1, 1), (D(-20), D(100), D(6), D(40), 0, -1), (D(30), D(70), D(-20), D(20), -1, -2)]

def side_leg(c, hip, thigh, knee, near, run=False):
    col = TROU[2] if near else TROU[1]
    kx, ky = limb(c, hip[0], hip[1], thigh, 3.2, 2, col)
    ax, ay = limb(c, kx, ky, thigh - knee, 3.0, 2, col)
    boot(c, int(round(ax)), int(round(ay)) + 1, 'side', front=near)

def figure(facing, mode='idle', k=0, eyes='open', hurt=False, crouch=0):
    """one pose. mode: idle (k 0..3 breath) | walk (k 0..7) | run (k 0..7)"""
    c = Canvas(W, H); cx = 12
    if mode == 'idle':
        breath = [0, 0, 1, 1][k]; bob = 0; g = None
    else:
        g = (RUN if mode == 'run' else WALK)[k]; bob = g[5]; breath = 0
    lag = 1 if (g and g[5] < 0) or (mode == 'idle' and k == 2) else 0           # hair / scarf / pack follow late
    ground = OY
    shoulder = ground - 17 + bob + (1 if hurt else 0) + crouch
    head_top = shoulder - 14 + (breath if mode == 'idle' else 0) * 0 + (1 if hurt else 0)
    lean = (1 if mode == 'run' else 0)
    if facing == 'side':
        hip = (cx + (1 if mode == 'run' else 0), ground - 8 + bob)
        # far arm and far leg first (darker), then body, then near limbs
        if g:
            side_leg(c, (hip[0] - 1, hip[1]), g[2], g[3], near=False)
            sw = g[4]; ang = D(-30) * sw if mode == 'walk' else D(-60) * sw
            ex, ey = limb(c, cx - 1, shoulder + 2, -ang, 3, 2, KNIT[0]); limb(c, ex, ey, -ang + (D(50) if mode == 'run' else D(15)), 2.6, 2, SKIN[3])
        else:
            for kk in (0,):
                limb(c, hip[0] - 1, hip[1], D(-4), 3.2, 2, TROU[1]); limb(c, hip[0] - 1.2, hip[1] + 3, D(-4), 3.0, 2, TROU[1]); boot(c, hip[0] - 2, ground, 'side', front=False)
        torso(c, 'side', cx + lean, shoulder, breath, scarf_lag=lag + (1 if mode == 'run' else 0), pack_lag=lag)
        if g: side_leg(c, hip, g[0], g[1], near=True)
        else: limb(c, hip[0] + 1, hip[1], D(4), 3.2, 2, TROU[2]); limb(c, hip[0] + 1.2, hip[1] + 3, D(2), 3.0, 2, TROU[2]); boot(c, hip[0] + 1, ground, 'side')
        sw = g[4] if g else 0; ang = (D(30) if mode != 'run' else D(60)) * sw
        if hurt: ang = D(40)
        ex, ey = limb(c, cx + 1 + lean, shoulder + 2 + (breath if mode == 'idle' else 0), ang, 3, 2, KNIT[2], KNIT[0])
        hx, hy = limb(c, ex, ey, ang + (D(70) if mode == 'run' or hurt else D(20) + max(0, ang)), 2.6, 2, KNIT[2], KNIT[0])
        disc(c, hx, hy + .5, 1, 1, SKIN[4])
        head(c, 'side', cx + 1 + lean, head_top + (breath if mode == 'idle' else 0), eyes, hair_lag=lag, mouth='wince' if hurt else 'smile')
    else:
        # legs: front/back view; the stepping foot lifts and the forward one reaches lower
        if g:
            lth, lkn, rth, rkn = g[0], g[1], g[2], g[3]
            for side, th, kn in ((-1, lth, lkn), (1, rth, rkn)):
                lift = int(round(max(0, math.sin(kn) * 2.4 - .3)))                 # knee bent: the foot is off the ground
                reach = 1 if th > D(15) else 0
                x = cx + side * 2 + (0 if side < 0 else 1)
                top = ground - 7 + bob
                y1 = ground - 2 - lift + reach
                for yy in range(top, y1): c.put(x - 1, yy, TROU[2] if side < 0 else TROU[1]); c.put(x, yy, TROU[2]); c.put(x + 1, yy, TROU[1])
                boot(c, x + 1, y1 + 2, facing, front=(reach == 1 or lift == 0))
        else:
            for side in (-1, 1):
                x = cx + side * 2 + (0 if side < 0 else 1)
                for yy in range(ground - 7 + crouch, ground - 2):
                    sp = side if crouch >= 2 and yy < ground - 3 else 0                       # knees splay out in a crouch
                    c.put(x - 1 + sp, yy, TROU[2] if side < 0 else TROU[1]); c.put(x + sp, yy, TROU[2]); c.put(x + 1 + sp, yy, TROU[1])
                if crouch >= 2: c.put(x + side * 2, ground - 4, TROU[3] if side < 0 else TROU[2])   # the knee catches the light
                boot(c, x + 1, ground, facing)
        sw = g[4] if g else 0
        torso(c, facing, cx, shoulder + (breath if mode == 'idle' and k >= 2 else 0) * 0, breath, scarf_lag=(lag if facing == 'down' else 0), pack_lag=lag)
        guard = 2 if hurt else 0
        arm_front(c, cx - 7, shoulder + 2, sw if facing == 'down' else -sw, -1, raised=guard + (1 if mode == 'run' else 0))
        arm_front(c, cx + 6, shoulder + 2, -sw if facing == 'down' else sw, 1, raised=guard + (1 if mode == 'run' else 0))
        head(c, facing, cx, head_top - (breath if mode == 'idle' and k in (2, 3) else 0) * 0 + (1 if mode == 'run' and facing == 'down' else 0), eyes, hair_lag=lag, mouth='wince' if hurt else 'smile')
        if mode == 'idle' and k in (2, 3):                                     # breath: the shoulders and head rise a pixel
            sub = Canvas(W, H); sub.a[:-1] = c.a[1:]; sub.a[ground - 6:] = c.a[ground - 6:]; c.a[:] = sub.a
    outline(c)
    return c

# ---------------------------------------------------------------- actions
def gather(k):
    """front view: bend, crouch, reach to the ground, pluck, look, rise"""
    crouch = [1, 2, 3, 3, 3, 1][k]
    c = figure('down', 'idle', 0, crouch=crouch)
    if k in (2, 3):                                                          # the right hand reaches down to the ground
        hx, hy = 18, OY - 3 + (0 if k == 2 else -1)
        for yy in range(OY - 13 + crouch, hy): c.put(hx, yy, KNIT[1]); c.put(hx + 1, yy, KNIT[0])
        c.rect(hx, hy, 2, 2, SKIN[4])
        if k == 3: c.put(hx + 2, hy, FY[1]); c.put(hx + 2, hy - 1, R('moss')[2])  # something small, and a leaf
    if k == 4:                                                               # holds it up to look at it
        c.rect(15, OY - 14 + crouch, 2, 2, SKIN[4]); c.put(16, OY - 15 + crouch, FY[1]); c.put(17, OY - 15 + crouch, R('moss')[2])
    outline(c); return c

def fish(k):
    """side view: cast back, swing, hold, hold, a little tug, hold"""
    c = figure('side', 'idle', [0, 0, 1, 2, 3, 2][k])
    rod = [(16, 20, 10, 4), (16, 20, 19, 3), (16, 21, 23, 9), (16, 21, 23, 10), (16, 21, 23, 12), (16, 21, 23, 10)][k]
    c.line(rod[0], rod[1], rod[2], rod[3], BOOT[3]); c.put(rod[2], rod[3], BOOT[4]); c.put(rod[0], rod[1], BOOT[1])
    c.rect(15, 20, 2, 2, SKIN[4])
    return c

def build(k):
    """front view hammer: raise, peak, strike, rebound, ready, strike"""
    c = figure('down', 'idle', [0, 2, 0, 0, 1, 0][k])
    hy = [14, 10, 20, 17, 14, 21][k]; hx = 19
    c.line(hx - 1, OY - 12, hx, hy + 2, BOOT[2])
    c.rect(hx - 1, hy, 3, 2, MT[2]); c.put(hx - 1, hy, MT[3])
    c.rect(hx - 2, OY - 13 + (1 if k in (2, 5) else 0), 2, 2, SKIN[4])
    return c

def sleep(k):
    """lying in a bedroll seen from above: pillow, sleepy face, liner folded back, breathing"""
    c = Canvas(W, H); rise = 1 if k == 1 else 0; y0 = OY - 11
    for y in range(y0, OY + 1):                                              # the roll itself, quilted
        for x in range(2, 22):
            if ((x - 12.5) / 10.2) ** 2 + ((y - (y0 + 5.5)) / 6.2) ** 2 <= 1: c.put(x, y, TROU[2] if (x + y) % 5 else TROU[1])
    for y in range(y0 + 1, OY): c.put(21, y, TROU[1]) if c.get(21, y) else None
    disc(c, 5.5, y0 + 5.5, 3.2, 4.2, PACK[2])                                # pillow
    disc(c, 6.5, y0 + 5.5, 3.6, 3.4, SKIN[4])                                # head
    for y in range(y0 + 2, y0 + 10):                                         # hair around the crown
        for x in range(2, 7):
            if ((x - 5.2) / 2.8) ** 2 + ((y - (y0 + 5.5)) / 4.0) ** 2 <= 1: c.put(x, y, HAIR[2])
    c.put(8, y0 + 4, BOOT[0]); c.put(8, y0 + 7, BOOT[0]); c.put(9, y0 + 5, SCARF[2])   # closed eyes, a warm cheek
    for y in range(y0 + 1 - rise, OY + rise): c.put(11, y, PACK[2]) if c.get(11, y) else None     # the liner folded back
    for y in range(y0 + 2 - rise, OY - 1 + rise): c.put(12, y, PACK[1]) if c.get(12, y) else None
    for y in range(y0 + 3, y0 + 8): c.put(10, y, SCARF[1])                   # scarf tucked in
    outline(c); return c

# ---------------------------------------------------------------- sheet
def cell(facing, col):
    name = FRAMES[col]
    if facing in ('down', 'up', 'side'):
        return figure(facing, 'idle', col) if col < 4 else figure(facing, 'walk', col - 4)
    if facing.startswith('run_'):
        f = facing[4:]; return figure(f, 'idle', col) if col < 4 else figure(f, 'run', col - 4)
    if facing == 'gather': return gather(col % 6)
    if facing == 'fish': return fish(col % 6)
    if facing == 'build': return build(col % 6)
    order = ['down', 'side', 'up']
    if facing == 'blink': return figure(order[col % 3], 'idle', 0 if col < 3 else 2, eyes='closed')
    if facing == 'hurt': return figure(order[col % 3], 'idle', 0, eyes='squeeze', hurt=True)
    if facing == 'sleep': return sleep(col % 2)

def build_sheet():
    sheet = Canvas(W * len(FRAMES), H * len(FACINGS))
    for fi, facing in enumerate(FACINGS):
        for ci in range(len(FRAMES)):
            sheet.blit(cell(facing, ci), ci * W, fi * H)
    meta = {'name': 'camper v3 (original player sprite: cozy proportions, jointed motion)', 'frame_w': W, 'frame_h': H, 'origin': [OX, OY],
            'facings': FACINGS, 'frames': FRAMES, 'rows': 'facing', 'cols': 'frame', 'side_flips_for_left': True,
            'idle_cols': IDLE_COLS, 'walk_cols': WALK_COLS, 'contacts': CONTACTS, 'walk_fps': 12, 'run_fps': 16, 'idle_fps': 2.2, 'foot_box': [8, 4],
            'action_frames': 6, 'action_fps': 7,
            'actions': {'gather': 'row 3, cols 0-5, kneel and pick', 'fish': 'row 4, cols 0-5, side facing', 'build': 'row 5, cols 0-5, hammer'},
            'run': {'rows': {'down': 'run_down', 'up': 'run_up', 'side': 'run_side'}, 'cols': WALK_COLS},
            'blink': {'row': 'blink', 'cols': {'down': 0, 'side': 1, 'up': 2}, 'lifted_offset': 3},
            'hurt': {'row': 'hurt', 'cols': {'down': 0, 'side': 1, 'up': 2}},
            'sleep': {'row': 'sleep', 'cols': [0, 1], 'fps': 0.6}}
    return sheet, meta

def export(out_dir):
    sheet, meta = build_sheet()
    os.makedirs(out_dir, exist_ok=True)
    from PIL import Image
    Image.fromarray(sheet.a, 'L').save(os.path.join(out_dir, 'player_idx.png'))
    sheet.save(os.path.join(out_dir, 'player_preview.png'), scale=1)
    json.dump(meta, open(os.path.join(out_dir, 'player.json'), 'w'), indent=1)
    return sheet, meta
