"""ORIGINAL player sprite v4: the camper, hand-drawn pixel by pixel.

16 x 32 px cells, feet on row 31 (origin 8, 31). Style target (from the user's reference screenshots, used for
proportion and readability only, nothing traced): slim figure about two tiles tall, a compact face under a wide
brim, crisp dark outline (warm red-brown on skin), flat 2-3 tone shading, arms hanging free with the hands at
the hips, short legs, sturdy boots, a soft ground shadow drawn by the engine.

The camper is our own: a soft felt field hat with a red band, dark hair, a rust field jacket over a cream shirt,
a red scarf knot at the collar, dark denim and brown boots.

Every frame below is an authored grid. Walk frames swap the arm and leg rows of the idle grid for authored
variants, so the head and jacket stay identical from frame to frame (no jitter).
"""
from __future__ import annotations
import json, os
from .canvas import Canvas
from .palette import PAL

W, H = 16, 32
OX, OY = 8, 31
FACINGS = ['down', 'up', 'side', 'gather', 'fish', 'build', 'run_down', 'run_up', 'run_side', 'blink', 'hurt', 'sleep']
FRAMES = ['idle0', 'idle1', 'walk0', 'walk1', 'walk2', 'walk3']
IDLE_COLS, WALK_COLS, CONTACTS = [0, 1], [2, 3, 4, 5], [3, 5]          # footsteps when the raised foot comes down

def r(f, k): return PAL.i(f, k)
PALETTE = {
    '.': 0,
    'o': r('wood', 0),        # outline
    'm': r('berry', 0),       # skin outline, warm
    'S': r('canvas', 5), 's': r('canvas', 4), 'c': r('canvas', 3),   # skin, skin shade, deep skin
    'W': r('flower_w', 2), 'G': r('fern', 1),                         # eye white, iris
    'H': r('earth', 3), 'e': r('earth', 4), 'K': r('earth', 2), 'k': r('earth', 1),   # felt hat: light, highlight, mid, under-brim
    'R': r('berry', 1), 'q': r('berry', 2),                           # red band / scarf, scarf highlight
    'h': r('wood', 1), 'x': r('wood', 2),                             # hair, hair light
    'J': r('leaf_litter', 1), 'L': r('leaf_litter', 2), 'j': r('leaf_litter', 0),   # jacket, jacket light, jacket shade
    'T': r('rope', 2), 't': r('rope', 1),                             # shirt, shirt shade
    'D': r('flower_b', 1), 'd': r('flower_b', 0), 'E': r('stone', 1), # denim, denim shade, deep
    'B': r('wood', 2), 'b': r('wood', 1), 'n': r('wood', 3),          # boot, boot shade, boot shine
}

def grid(rows):
    assert len(rows) == H, (len(rows), rows[0])
    c = Canvas(W, H)
    for y, row in enumerate(rows):
        assert len(row) == W, (y, row, len(row))
        for x, ch in enumerate(row):
            if ch != '.': c.put(x, y, PALETTE[ch])
    return c

# ================================================================= FRONT (facing the camera)
FRONT_TOP = [
    '................',
    '................',
    '................',
    '.....oooooo.....',
    '....oHeeHHHo....',
    '....oHeHHHKo....',
    '...oRRRRRRRRo...',
    '..ooKHHHHHHKoo..',
    '.oHHHHHHHHHHHHo.',
    'okHHkkkkkkkkHHko',
    'oo.ohhhhhhhho.oo',
    '...mhSSSSSShm...',
    '...mhWGSSGWhm...',
    '...mSSSccSSSm...',
    '....mmSSSSmm....',
    '....ojRqRRjo....',
    '...oJJjTRtjJJo..',
    '..oJLJjTTtjJLJo.',
    '..oJLojTTtjoLJo.',
    '..oJLojTTtjoLJo.',
    '..oJLojTTtjoLJo.',
    '..oJJojTTtjoJJo.',
    '..ojjojJJJjojjo.',
]
FRONT_LEGS = {  # rows 23..31: hands, belt, legs, boots
    'stand': ['..mSSmEdddEmSSm.', '..mscmdDDDdmscm.', '...mm.dDDdD.mm..', '.....odDoDdo....', '.....odDoDdo....', '....obBBoBBbo...', '....oBnBoBnBo...', '....ooooooooo...', '................'],
    'left':  ['..mSSmEdddEmSSm.', '..mscmdDDDdmscm.', '...mm.dDDdD.mm..', '.....odDoDdo....', '.....odDoBBo....', '....obBBoBnBo...', '....oBnBoooo....', '....ooooo.......', '................'],   # left foot forward and down, right foot lifts
    'right': ['..mSSmEdddEmSSm.', '..mscmdDDDdmscm.', '...mm.dDDdD.mm..', '.....odDoDdo....', '.....oBBoDdo....', '....oBnBobBBo...', '.....ooooBnBo...', '........ooooo...', '................'],
    # foot up: the right knee comes up toward you, the boot lifts clear of the ground and shows its sole
    'up':    ['..mSSmEdddEmSSm.', '..mscmdDDDdmscm.', '...mm.dDDdDd.mm.', '.....odDodDDo...', '.....odDobBBo...', '.....odDoBnBo...', '....obBBoooo....', '....oBnBo.......', '....ooooo.......'],
}
# arm swing (front): the hand on the stepping side moves back (up a row), the other forward
def swing(rows, legs):
    """the hand on the side of the forward foot swings back (up a row), the other forward (down a row)"""
    if legs not in ('left', 'right'): return rows
    up, down = ((2, 6), (11, 15)) if legs == 'left' else ((11, 15), (2, 6))
    def shift(x0, x1, dy):
        src = [r[x0:x1] for r in rows]
        for y in range(21, 27):
            sy = y - dy
            rows[y][x0:x1] = src[sy] if 21 <= sy < 27 else list('.' * (x1 - x0))
    shift(*up, -1); shift(*down, 1)
    for x0, x1 in (up, down):                     # keep the cuff closed where a hand moved down
        for x in range(x0, x1):
            if rows[21][x] == '.' and rows[20][x] != '.': rows[21][x] = rows[20][x]
    return rows

def front(kind, legs='stand', blink=False, hurt=False):
    rows = [list(x) for x in FRONT_TOP + FRONT_LEGS[legs]]
    if blink: rows[12] = list('...mhSccccShm...'.replace('cccc', 'cSSc'))
    if hurt: rows[12] = list('...mhoSSSSohm...'); rows[13] = list('...mSScccSSSm...')
    return grid([''.join(x) for x in swing(rows, legs)])

# ================================================================= BACK (walking away)
BACK_TOP = [
    '................',
    '................',
    '................',
    '.....oooooo.....',
    '....oHeHHHHo....',
    '....oHHHHHKo....',
    '...oRRRRRRRRo...',
    '..ooKHHHHHHKoo..',
    '.oHHHHHHHHHHHHo.',
    'okHHkkkkkkkkHHko',
    'oo.ohhhhhhhho.oo',
    '...ohhhhhhhho...',
    '...ohhhhhhhho...',
    '...ohhhhhhhho...',
    '....mhhhhhhm....',
    '....ojRRRRjo....',
    '...oJJJJJJJJo...',
    '..oJLJJJJJJjJo..',
    '..oJLoJJJJjojJo.',
    '..oJLoJLJJjojJo.',
    '..oJLoJJJJjojJo.',
    '..oJJoJJJJjojJo.',
    '..ojjojjjjjojjo.',
]
def back(legs='stand'):
    rows = [list(x) for x in BACK_TOP + FRONT_LEGS[legs]]
    rows[23][6:11] = list('EdddE'); rows[24][6:11] = list('dDDDd')
    return grid([''.join(x) for x in swing(rows, legs)])

# ================================================================= SIDE (facing right; flipped for left)
SIDE_TOP = [
    '................',
    '................',
    '................',
    '....oooooo......',
    '...oHeeHHHo.....',
    '...oHeHHHKo.....',
    '..oRRRRRRRRo....',
    '.ooKHHHHHHHKoo..',
    'oHHHHHHHHHHHHHo.',
    'okkkkkkkkkkHHHko',
    'o..ohhhhhSSSmo.o',
    '...ohhhhSSSSSm..',
    '...ohhhhSSWGSm..',
    '....ohhhSSSScm..',
    '....omhhmSSmm...',
    '.....ojRqRo.....',
    '....oJJjRtJo....',
    '....oJJJjtJo....',
    '....ojJLLJJo....',
    '....ojJLLJJo....',
    '....ojJJLJJo....',
    '....ojJJLJJo....',
    '....ojjJJjjo....',
]
SIDE_LEGS = {
    'stand':  ['.....oommSSm....', '.....odDmscm....', '.....odDDmmo....', '.....odDDDo.....', '.....odDDDo.....', '.....obBBBBo....', '.....oBnBBBBo...', '.....oooooooo...', '................'],
    'stride': ['.....oommSSm....', '.....odDmscm....', '.....odDDmmo....', '.....odDDDo.....', '....odDodDDo....', '....obBo.oBBo...', '...oBnBo.oBnBBo.', '...oooo..oooooo.', '................'],   # contact: a short, honest step
    # foot up 90 degrees: the near thigh level with the hip, the shin hanging straight down, the boot off the ground
    'up':     ['.....oommSSm....', '.....odDmscm....', '.....odDDDDDo...', '.....odDddDDDo..', '.....odDo.oDDo..', '.....obBBooBBBo.', '.....oBnBBooooo.', '.....oooooo.....', '................'],
    'pass':   ['.....oommSSm....', '.....odDmscm....', '.....odDDmmo....', '.....odDDDo.....', '.....odDBBo.....', '.....obBnBBo....', '.....oBBBBBBo...', '.....oooooooo...', '................'],   # passing: the back foot lifts
}
def side(legs='stand', arm='rest', blink=False, hurt=False):
    rows = [list(x) for x in SIDE_TOP + SIDE_LEGS[legs]]
    if arm == 'back':      # near arm swings back: hand behind the hip
        rows[19][6:9] = list('JLL'); rows[21][5:8] = list('jLJ'); rows[22][4:8] = list('ojLo')
        rows[23][4:12] = list('omSSmoo.') if legs != 'stride' else rows[23][4:12]
        rows[23][8:12] = list('ommo') if legs == 'stride' else rows[23][8:12]
        rows[23][3:7] = list('mSSm'); rows[24][3:7] = list('mscm'); rows[24][7:12] = list(''.join(rows[24][7:12]).replace('m', 'D').replace('s', 'D').replace('c', 'D'))
        rows[25][3:6] = list('.mm')
    if arm == 'fwd':       # near arm swings forward: hand in front of the belly
        rows[21][9:13] = list('LJjo'); rows[22][9:13] = list('Jjmo'); rows[23][9:13] = list('SSm.'); rows[24][9:13] = list('scm.'); rows[25][9:12] = list('mm.')
    if blink: rows[12][10:12] = list('cc')
    if hurt: rows[12][10:12] = list('oo'); rows[13][9:12] = list('ccc')
    return grid([''.join(x) for x in rows])

# ================================================================= frames
def bob(c, dy):
    """the body rises a pixel on passing frames (the head and jacket ride on the legs)"""
    if not dy: return c
    o = Canvas(W, H); o.a[:H - 9 + dy] = c.a[-dy:H - 9]; o.a[H - 9 + dy:] = c.a[H - 9 + dy:]
    return o

def walk_frames(facing, run=False):
    """two images only: foot up, standing, foot up, standing (the user's brief: no in-betweens, no bob, no swing)"""
    up = {'down': front('walk', 'up'), 'up': back('up'), 'side': side('up')}[facing]
    stand = {'down': front('idle'), 'up': back(), 'side': side()}[facing]
    return [up, stand, up, stand]

def idle_frames(facing):
    base = {'down': front('idle'), 'up': back(), 'side': side()}[facing]
    return [base, base]                                                   # standing still means standing still

def breathe(c):
    o = Canvas(W, H); o.a[:] = c.a; return o                              # kept for the blink row layout; no motion

def action(kind, k):
    if kind == 'gather':   # crouch and reach (front)
        c = front('idle'); d = [0, 1, 2, 2][k]
        if d: o = Canvas(W, H); o.a[d:H - 6] = c.a[:H - 6 - d]; o.a[H - 6:] = c.a[H - 6:]; c = o
        if k >= 2: c.put(13, 29, PALETTE['S']); c.put(14, 29, PALETTE['S']); c.put(13, 30, PALETTE['m']); c.put(14, 28, PALETTE['m'])
        if k == 3: c.put(15, 28, r('flower_y', 1))
        return c
    if kind == 'fish':     # side, rod out over the water
        c = side(arm='fwd'); tips = [(9, 6), (15, 2), (15, 4), (15, 5)][k]
        c.line(11, 22, tips[0], tips[1], r('wood', 3)); c.put(tips[0], tips[1], r('wood', 4)); return c
    if kind == 'build':    # front, hammer up and down
        c = front('idle'); hy = [14, 11, 19, 22][k]
        c.line(13, 22, 14, hy + 2, r('wood', 2)); c.rect(13, hy, 3, 2, r('metal', 2)); c.put(13, hy, r('metal', 3)); return c

def sleep(k):
    c = Canvas(W, H); y0 = 22
    for y in range(y0, 31):
        for x in range(1, 15):
            if ((x - 7.5) / 7.2) ** 2 + ((y - 26.5) / 4.6) ** 2 <= 1: c.put(x, y, PALETTE['J'] if (x + y) % 6 else PALETTE['j'])
    for y in range(y0 + 1 - k, 30): c.put(8, y, PALETTE['T']) if c.get(8, y) else None
    for (x, y, ch) in [(3, 25, 'h'), (4, 25, 'h'), (2, 26, 'h'), (3, 26, 'S'), (4, 26, 'S'), (5, 26, 'S'), (3, 27, 'S'), (4, 27, 'c'), (5, 27, 'S'), (3, 28, 'm'), (4, 28, 'm'), (6, 26, 'R'), (6, 27, 'R')]:
        c.put(x, y, PALETTE[ch])
    from .camper import outline as _outline
    _outline(c); return c

def cell(facing, col):
    if facing in ('down', 'up', 'side'):
        return idle_frames(facing)[col] if col < 2 else walk_frames(facing)[col - 2]
    if facing.startswith('run_'):
        f = facing[4:]; return idle_frames(f)[col] if col < 2 else walk_frames(f, run=True)[col - 2]
    if facing in ('gather', 'fish', 'build'): return action(facing, col % 4)
    order = ['down', 'side', 'up']
    f = order[col % 3]
    if facing == 'blink':
        c = front('idle', blink=True) if f == 'down' else side(blink=True) if f == 'side' else back()
        return breathe(c) if col >= 3 else c
    if facing == 'hurt': return front('idle', hurt=True) if f == 'down' else side(hurt=True) if f == 'side' else back()
    if facing == 'sleep': return sleep(col % 2)

def build_sheet():
    sheet = Canvas(W * len(FRAMES), H * len(FACINGS))
    for fi, facing in enumerate(FACINGS):
        for ci in range(len(FRAMES)):
            sheet.blit(cell(facing, ci), ci * W, fi * H)
    meta = {'name': 'camper v4 (original, hand-drawn; slim proportions under a wide felt hat)', 'frame_w': W, 'frame_h': H, 'origin': [OX, OY],
            'facings': FACINGS, 'frames': FRAMES, 'rows': 'facing', 'cols': 'frame', 'side_flips_for_left': True,
            'idle_cols': IDLE_COLS, 'walk_cols': WALK_COLS, 'contacts': CONTACTS, 'walk_fps': 6, 'run_fps': 10, 'idle_fps': 1.0, 'foot_box': [8, 4],
            'action_frames': 4, 'action_fps': 6, 'shadow': [6, 2],
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
