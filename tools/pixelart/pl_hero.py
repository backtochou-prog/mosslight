"""The protagonist, from PixelLab (create_character from the approved hero_south design, then animate_character).

Sources: assets/pixellab/src/hero/ (tools/pixellab/hero.py downloads them): rotations/<dir>.png and
<animation>/<dir>/<i>.png. The 32x40 clips share the rotations' registration; the custom clips (fishing, hammering)
come on a 44x44 canvas and are registered by matching their first frame (the reference pose) to the rotation.

Every pixel goes onto the game palette (the hero families), so night, season and weather tables keep working.
The sheet keeps the layout play.html reads: rows are facings and actions, columns are idle then walk frames; the side
row faces right and is flipped for left.
"""
from __future__ import annotations
import os, json, glob
import numpy as np
from PIL import Image
from .canvas import Canvas
from .palette import PAL
from .pl_pilot import to_palette

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'assets/pixellab/src/hero')
FAMS = json.load(open(os.path.join(ROOT, 'assets/pixellab/pilot.json')))['hero_south']['palette_families']

CW, CH = 48, 40                     # cell: room for the cast rod in front
PX, PY = 8, 2                       # where a rotation's (0, 0) lands in the cell
DIR = {'down': 'south', 'up': 'north', 'side': 'east'}
IDLE, WALK = 4, 6
FACINGS = ['down', 'up', 'side', 'gather', 'fish', 'build', 'run_down', 'run_up', 'run_side', 'blink', 'hurt', 'sleep']
FRAMES = [f'idle{i}' for i in range(IDLE)] + [f'walk{i}' for i in range(WALK)]
# action clips: (animation, direction, source frames for the four action columns)
ACTIONS = {'gather': ('picking-up', 'south', [0, 1, 3, 4]),       # frame 2 of the south pick-up came out mangled
           'fish': ('fishing', 'east', [4, 4, 4, 4]),             # rod held out over the water; the float and line give the life
           'build': ('hammering', 'south', [1, 2, 3, 4])}
HURT = ('taking-punch', {'down': 2, 'side': 1, 'up': 1})          # the gentle recoil frames; the later side frames swing a fist
SKIN = [PAL.index[('shroom', 3)], PAL.index[('shroom', 2)]]
LID = PAL.index[('wood', 1)]


def _frames(anim, d):
    ps = sorted(glob.glob(os.path.join(SRC, anim, d, '*.png')), key=lambda p: int(os.path.basename(p)[:-4]))
    return [np.array(Image.open(p).convert('RGBA')) for p in ps]


def _rotation(d):
    return np.array(Image.open(os.path.join(SRC, 'rotations', d + '.png')).convert('RGBA'))


def _offset(first, d):
    """Where the rotation sits inside a bigger custom canvas: the shift that makes the most pixels agree."""
    rot = _rotation(d); h, w = rot.shape[:2]; H, W = first.shape[:2]
    if (H, W) == (h, w): return 0, 0
    best, bo = -1, (0, 0)
    for dy in range(H - h + 1):
        for dx in range(W - w + 1):
            sub = first[dy:dy + h, dx:dx + w]; m = (sub[:, :, 3] >= 128) & (rot[:, :, 3] >= 128)
            s = int((np.abs(sub[:, :, :3].astype(int) - rot[:, :, :3]).sum(2)[m] < 30).sum()) - int(((sub[:, :, 3] >= 128) ^ (rot[:, :, 3] >= 128)).sum())
            if s > best: best, bo = s, (dx, dy)
    return bo


def _cell(rgba, off=(0, 0)):
    """One source frame onto a cell, on the palette."""
    c, _ = to_palette(rgba, FAMS)
    out = Canvas(CW, CH); dx, dy = off
    h, w = c.a.shape
    for y in range(h):
        cy = y - dy + PY
        if not 0 <= cy < CH: continue
        for x in range(w):
            cx = x - dx + PX
            if 0 <= cx < CW and c.a[y, x]: out.a[cy, cx] = c.a[y, x]
    return out


def _clip(anim, d, picks=None):
    fr = _frames(anim, d)
    if not fr: return []
    off = _offset(fr[0], d)
    return [_cell(fr[i], off) for i in (picks if picks is not None else range(len(fr)))]


def eyes_closed(c):
    """Blink: the dark pixels inside the face (skin all around them, left and right) become skin, and a short lid line
    is drawn on the lower row of each eye."""
    a = c.a.copy(); sk = np.isin(a, SKIN)
    rows = np.nonzero(sk.any(1))[0]
    if not len(rows): return c
    top = rows.min(); out = c.copy()
    eye = np.zeros_like(sk)
    for y in range(top, min(top + 6, a.shape[0])):
        xs = np.nonzero(sk[y])[0]
        if len(xs) < 3: continue
        for x in range(xs.min() + 1, xs.max()):
            if a[y, x] and not sk[y, x] and (sk[y, x - 1] or sk[y, x + 1]) and (sk[y - 1, x] or sk[y + 1, x]): eye[y, x] = True
    if not eye.any(): return c
    out.a[eye] = SKIN[0]
    for x in np.unique(np.nonzero(eye)[1]):
        ys = np.nonzero(eye[:, x])[0]; out.a[ys.max(), x] = LID
    return out


def sleeper(k):
    """Asleep in the bedroll: the front pose with the eyes shut, laid down head-left on a small pillow, a quilted
    bedroll pulled up to the shoulders. k=1 is the in-breath (the roll one pixel higher)."""
    face = eyes_closed(_cell(_rotation('south')))
    a = np.rot90(face.a, 1); ys, xs = np.nonzero(a)                   # head to the left, feet to the right
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]; h, w = a.shape
    out = Canvas(CW, CH); ox, oy = _origin()
    x0, y0 = ox - w // 2 - 2, oy - h + 1
    rope = [PAL.index[('rope', i)] for i in range(len(PAL.ramp('rope')))]
    wood0, sheet = PAL.index[('wood', 0)], PAL.index[('flower_w', 1)]
    fo = [PAL.index[('forest', i)] for i in range(5)]                    # the roll is the vest's green
    # pillow under the head
    for y in range(y0 + 3, y0 + h - 2):
        for x in range(x0 - 3, x0 + 6): out.a[y, x] = rope[-1] if x0 - 3 < x < x0 + 5 and y0 + 3 < y < y0 + h - 3 else wood0
    for y in range(h):
        for x in range(w):
            if a[y, x]: out.a[y0 + y, x0 + x] = a[y, x]
    # the face's skin ends at the neck; the roll starts there
    sk = np.isin(a, SKIN).any(0)[:w // 2 + 1]; neck = int(np.nonzero(sk)[0].max()) + 1     # the face only (the hands lie further down)
    bx0, bx1 = x0 + neck, min(CW - 2, x0 + w + 2); by0, by1 = y0 + 1 - k, y0 + h - 1
    out.a[:by0, bx0:] = 0                                                  # nothing of the body shows above the roll
    for y in range(by0, by1 + 1):
        for x in range(bx0, bx1 + 1):
            corner = (y in (by0, by1)) and (x in (bx0, bx1))
            if corner: continue
            edge = y in (by0, by1) or x in (bx0, bx1)
            out.a[y, x] = fo[0] if edge else (fo[3] if y <= by0 + 2 else fo[2] if y < by1 - 2 else fo[1])
    for y in range(by0 + 1, by1): out.a[y, bx0 + 2] = sheet                 # the turned-down sheet at the shoulders
    for x in range(bx0 + 7, bx1 - 1, 6):                                     # quilting
        for y in range(by0 + 2, by1 - 1): out.a[y, x] = fo[1]
    return out


def _origin():
    rot = _rotation('south'); ys, xs = np.nonzero(rot[:, :, 3] >= 128)
    feet = xs[ys >= ys.max() - 2]
    return int(round((feet.min() + feet.max()) / 2)) + PX, int(ys.max()) + PY


def _contacts(walk):
    """The two walk frames where the stride is widest (both feet down): the footstep sounds play on these."""
    spread = []
    for c in walk:
        m = c.a != 0; ys = np.nonzero(m.any(1))[0]; b = ys.max()
        xs = np.nonzero(m[b - 2:b + 1].any(0))[0]; spread.append(xs.max() - xs.min())
    order = sorted(range(len(walk)), key=lambda i: -spread[i])
    a = order[0]; b = next(i for i in order[1:] if abs(i - a) >= 2 and abs(i - a) <= len(walk) - 2)
    return sorted([IDLE + a, IDLE + b])


def _rod_tip(c, origin):
    m = c.a != 0; ys, xs = np.nonzero(m[:origin[1] - 8])
    i = xs.argmax(); return [int(xs[i] - origin[0]), int(ys[i] - origin[1])]


def build_sheet():
    ox, oy = _origin()
    sheet = Canvas(CW * len(FRAMES), CH * len(FACINGS))
    put = lambda c, row, col: sheet.blit(c, col * CW, FACINGS.index(row) * CH)
    idle, walk = {}, {}
    for f, d in DIR.items():
        idle[f] = _clip('breathing-idle', d); walk[f] = _clip('walking', d)
        run = _clip('running-6-frames', d) or walk[f]
        for i, c in enumerate(idle[f]): put(c, f, i); put(c, 'run_' + f, i)
        for i, c in enumerate(walk[f]): put(c, f, IDLE + i)
        for i, c in enumerate(run[:WALK]): put(c, 'run_' + f, IDLE + i)
    for act, (anim, d, picks) in ACTIONS.items():
        for i, c in enumerate(_clip(anim, d, picks)): put(c, act, i)
    fish = _clip(*ACTIONS['fish'][:2], [ACTIONS['fish'][2][0]])[0]
    for i in range(IDLE):
        put(eyes_closed(idle['down'][i]), 'blink', i); put(eyes_closed(idle['side'][i]), 'blink', IDLE + i)
    for j, f in enumerate(('down', 'side', 'up')):
        h = _clip(HURT[0], DIR[f]); put(h[min(HURT[1][f], len(h) - 1)] if h else eyes_closed(idle[f][0]), 'hurt', j)
    put(sleeper(0), 'sleep', 0); put(sleeper(1), 'sleep', 1)
    meta = {'name': 'MOSSlight protagonist (PixelLab character on the game palette)', 'frame_w': CW, 'frame_h': CH, 'origin': [ox, oy],
            'facings': FACINGS, 'frames': FRAMES, 'rows': 'facing', 'cols': 'frame', 'side_flips_for_left': True,
            'idle_cols': list(range(IDLE)), 'walk_cols': list(range(IDLE, IDLE + WALK)), 'contacts': _contacts(walk['side']),
            'walk_fps': 10, 'run_fps': 14, 'idle_fps': 2.2, 'foot_box': [8, 4], 'action_frames': 4, 'action_fps': 6, 'shadow': [7, 2],
            'rod_tip': _rod_tip(fish, (ox, oy)),
            'run': {'rows': {'down': 'run_down', 'up': 'run_up', 'side': 'run_side'}, 'cols': list(range(IDLE, IDLE + WALK))},
            'blink': {'row': 'blink', 'per_idle': {'down': 0, 'side': IDLE}},
            'hurt': {'row': 'hurt', 'cols': {'down': 0, 'side': 1, 'up': 2}},
            'sleep': {'row': 'sleep', 'cols': [0, 1], 'fps': 0.6}}
    return sheet, meta


def available():
    return os.path.exists(os.path.join(SRC, 'walking', 'south'))


def export(out_dir):
    sheet, meta = build_sheet(); os.makedirs(out_dir, exist_ok=True)
    Image.fromarray(sheet.a, 'L').save(os.path.join(out_dir, 'player_idx.png')); sheet.save(os.path.join(out_dir, 'player_preview.png'), scale=1)
    json.dump(meta, open(os.path.join(out_dir, 'player.json'), 'w'), indent=1); return sheet, meta
