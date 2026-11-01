"""Fish plate engine. Fish are collected and studied, so they get their own indexed plate palette
(the world palette has no free slots) and an anatomy-first renderer: a swept body along a spine with
top/bottom profiles, fins with rays, tails by type, jaws, barbels, markings placed in body coordinates.
Each species is an individual anatomical description, never a recolour of a template.
Plates face left, fit 32x32, and are shown at native size in the pack and enlarged in the field book."""
from __future__ import annotations
import math, random
import numpy as np
from .canvas import Canvas

RAMPS = {
 'silver': ['2c3a48','4f6272','7f919c','aebbc0','d8e0de','f6f8f0'], 'steel': ['1f2c3e','34495f','527083','7a99a8','a8c3c8','d8e8e4'],
 'olive': ['25301a','3d4c22','5d6a2c','818a3a','a9aa52','d0c978'], 'moss': ['17331f','27502a','3f7433','649a40','90bd56','bfdc7c'],
 'gold': ['5a3510','8d5a14','c0861c','e6b02e','f7d55a','fff0a8'], 'amber': ['43240e','6e3e12','9d6118','c98a28','e6b352','f6d88e'],
 'copper': ['3e1d12','6b3216','9a4e1e','c4702e','e09a52','f2c48a'], 'rust': ['2f120e','571f14','82301a','aa4a22','c97238','e2a062'],
 'rose': ['5a2036','8a3650','b85a70','d98a94','efb6b4','fbdeD4'], 'crimson': ['3e0c16','701420','a42028','d0382e','ea6a48','f7a678'],
 'orange': ['5c200c','93380e','c95a12','ec8420','f8ae44','ffd686'], 'lemon': ['5e5212','8e8018','bcae26','e0d23c','f3e96c','fdf8b4'],
 'teal': ['0e2f33','14494c','1f6c68','349286','5eb8a0','9cdcc0'], 'aqua': ['124258','1a6680','2c90a8','52b8c4','8cdcd8','ccf6ec'],
 'cobalt': ['101f52','182f7c','2448a8','3a6cc8','6c9ce0','aacdf2'], 'indigo': ['16123c','261f5e','3b3186','5a4cac','8378cc','b4ace4'],
 'violet': ['2c1244','4a1f68','6e3490','9558b0','bc8ccc','e0c4e6'], 'plum': ['2a1020','471a32','672a48','8a4460','ad6e84','d2a4ac'],
 'umber': ['241810','3e2a1a','5a4026','785a38','98785019'[:6],'bca078'], 'mud': ['1e1c12','34301c','4e4828','6a6236','8a8250','aea678'],
 'char': ['101214','1e2226','2e3338','44494e','62686a','8a908e'], 'ink': ['06080e','0e1420','18202e','242e40','364458','506478'],
 'bone': ['6c6450','948a70','b8ae92','d4ccb2','eae4ce','faf6e6'], 'ivory': ['a08c7c','c4ae9c','dcc8b8','eee0d0','f8f0e4','fffcf4'],
 'flesh': ['8a5a58','b07c74','cca094','e2c0b0','f2dccc','fcf0e6'], 'glow': ['0f4c5c','147c88','22b0b0','4adcc8','94f4dc','e4fff0'],
 'lume': ['1e4a24','2c7c34','4cb048','84d85c','bef080','f2ffc0'], 'moon': ['2c3a68','4c5e94','7c90bc','a8bcdc','d0dcf0','f4f8ff'],
 'ember': ['4a1006','8c1c08','cc3a0c','f4701c','ffae3c','ffe88c'], 'black': ['040406','0c0c12','16161e','22222c','34343f','4c4c58'],
}
FAMS = list(RAMPS); IDX = {}; PALETTE = [(0, 0, 0)]
for _f in FAMS:
    for _r, _h in enumerate(RAMPS[_f]): IDX[(_f, _r)] = len(PALETTE); PALETTE.append(tuple(int(_h[i:i + 2], 16) for i in (0, 2, 4)))
assert len(PALETTE) < 256
FAM_OF = {v: k for k, v in IDX.items()}
def ci(f, r): return IDX[(f, max(0, min(5, int(round(r)))))]

def curve(pts):
    """Smooth profile through (t, value) control points."""
    pts = sorted(pts)
    def f(t):
        if t <= pts[0][0]: return pts[0][1]
        for (a, av), (b, bv) in zip(pts, pts[1:]):
            if t <= b: u = (t - a) / (b - a or 1); u = u * u * (3 - 2 * u); return av + (bv - av) * u
        return pts[-1][1]
    return f
def straight(L, arch=0.0): return lambda s: (s * L, -arch * math.sin(s * math.pi))
def wave(L, a, n, ph=0.0): return lambda s: (s * L, a * math.sin(s * math.pi * 2 * n + ph) * (.35 + .65 * s))
def path(pts):
    """Spine through arbitrary (x, y) points (Catmull-Rom): coils and bends."""
    P = [pts[0]] + list(pts) + [pts[-1]]; n = len(pts) - 1
    def f(s):
        q = min(n - 1e-6, s * n); i = int(q); u = q - i; a, b, c, d = P[i], P[i + 1], P[i + 2], P[i + 3]
        g = lambda k: .5 * (2 * b[k] + (c[k] - a[k]) * u + (2 * a[k] - 5 * b[k] + 4 * c[k] - d[k]) * u * u + (3 * b[k] - a[k] - 3 * c[k] + d[k]) * u * u * u)
        return (g(0), g(1))
    return f

class Plate:
    def __init__(self, sp):
        self.sp = sp; self.S = 96; self.id = np.zeros((self.S, self.S), dtype=np.uint8); self.rng = random.Random(sp.get('seed', sum(map(ord, sp['id']))))
        self.spine = sp['spine']; self.top = curve(sp['top']); self.bot = curve(sp['bot']); self.ox, self.oy = 30, 48
        self.body = np.zeros((self.S, self.S), dtype=bool)
    def at(self, s, off, along=0.0):
        x, y = self.spine(s); x2, y2 = self.spine(min(1, s + .01)); x1, y1 = self.spine(max(0, s - .01)); dx, dy = x2 - x1, y2 - y1; d = math.hypot(dx, dy) or 1; dx, dy = dx / d, dy / d
        return (self.ox + x + dy * off + dx * along, self.oy + y - dx * off + dy * along)
    def plot(self, x, y, i):
        xi, yi = int(math.floor(x)), int(math.floor(y))
        if 0 <= xi < self.S and 0 <= yi < self.S: self.id[yi, xi] = i
    # ---- fins
    def fin(self, t0, t1, h, shape='round', side=1, ramp=None, skew=.7, rays=2, edge=None, tip=None, base=None):
        """Membrane swept off the body edge. shape: sail, round, low, spiny, pennant, flag, ribbon, fan."""
        ramp = ramp or self.sp['fin']; prof = self.top if side > 0 else self.bot
        SH = {'sail': lambda u: (.35 + .65 * min(1, u * 4)) * (1 - .75 * u), 'round': lambda u: math.sin(u * math.pi) ** .6, 'low': lambda u: min(1, u * 5) * min(1, (1 - u) * 5) * .8 + .2,
              'spiny': lambda u: (.55 + .45 * math.sin(u * math.pi)) * (.72 if int(u * 40) % 4 == 3 else 1), 'pennant': lambda u: max(.15, 1 - u * 1.25) ** 1.4, 'flag': lambda u: 1 - .55 * u,
              'ribbon': lambda u: .8 + .2 * math.sin(u * 24), 'fan': lambda u: .25 + .75 * math.sin(u * math.pi * .62) ** 1.2}[shape]
        n = int(max(8, (t1 - t0) * 400)); base_off = None
        for k in range(n + 1):
            u = k / n; s = t0 + (t1 - t0) * u; b = prof(s) - .6; H = h * SH(u); steps = int(H * 3) + 1
            xs, _ = self.at(s, 0); ray = int(xs) // rays
            for q in range(steps + 1):
                f = q / max(1, steps); off = (b + f * H) * side; x, y = self.at(s, off, f * H * skew)
                r = 3 + (ray % 2) * .9 - f * 1.5
                col = ramp
                if base and f < .35: col = base
                if tip and f > .62: col = tip; r = 3 + (ray % 2)
                if edge and f > .9: col = edge; r = 3
                self.plot(x, y, ci(col, r))
    def paddle(self, s, off, length, width, ang, ramp=None, rank=3, tip=None):
        """Paired fin as a small fan: pectoral (drawn over the body) or pelvic."""
        ramp = ramp or self.sp['fin']; x0, y0 = self.at(s, off); a = math.radians(ang)
        for k in range(int(length * 3) + 1):
            f = k / max(1, length * 3); w = width * math.sin(min(1, f * 1.15) * math.pi * .72 + .15)
            for q in np.arange(-w, w + .01, .33):
                x = x0 + math.cos(a) * f * length - math.sin(a) * q; y = y0 + math.sin(a) * f * length + math.cos(a) * q
                ray = int((q + w) / 1.4) % 2
                self.plot(x, y, ci(tip if tip and f > .65 else ramp, rank + ray - (f * .9)))
    def tail(self, kind, size, ramp=None, spread=None, tip=None, s=1.0):
        """Caudal fin by type: fork, deep, square, round, lunate, lance, fan, whip, broom."""
        ramp = ramp or self.sp['fin']; x0, y0 = self.at(s, 0); x1, y1 = self.at(s - .03, 0); a0 = math.atan2(y0 - y1, x0 - x1)
        sp = spread or size * .62
        def outer(v):      # length of the ray at vertical position v in -1..1
            av = abs(v)
            return {'fork': .55 + .45 * av ** 1.1, 'deep': .3 + .7 * av ** .9, 'square': .95 + .05 * av, 'round': 1 - .3 * av ** 2, 'lunate': .28 + .72 * av ** .6, 'lance': max(.1, 1 - av * 1.1) ** 1.3,
                    'fan': 1 - .12 * av, 'whip': max(.05, 1 - av * 1.7) ** 2, 'broom': .8 + .3 * math.sin(v * 9)}[kind]
        n = int(sp * 8) + 2
        for k in range(-n, n + 1):
            v = k / n; L = size * outer(v); b = a0 + v * math.atan2(sp, size * .9); ray = (k // 3) % 2; steps = int(L * 3) + 1
            for q in range(steps + 1):
                f = q / steps; x = x0 + math.cos(b) * f * L; y = y0 + math.sin(b) * f * L
                r = 3 + ray * .9 - f * 1.1; c = tip if tip and f > .68 else ramp
                self.plot(x, y, ci(c, r))
    # ---- body
    def draw_body(self):
        sp = self.sp; L = sp.get('steps', 700); back, flank, belly = sp['back'], sp['flank'], sp['belly']; sc = sp.get('scales', 0); pats = sp.get('marks', []); bs, fs = sp.get('split', (.28, .68))
        lo, hi = sp.get('ranks', (1, 4)); g = sp.get('gloss', .36)
        for k in range(L + 1):
            s = k / L; t, b = self.top(s), self.bot(s); H = t + b
            if H <= 0: continue
            for q in range(int(H * 3) + 1):
                v = q / max(1, int(H * 3)); x, y = self.at(s, t - v * H); xi, yi = int(x), int(y)
                if not (0 <= xi < self.S and 0 <= yi < self.S): continue
                n = 1 - min(1, abs(v - g) * 2.0); lit = lo + (hi - lo) * n
                fam = back if v < bs + .03 * math.sin(s * 19) else (belly if v > fs + .03 * math.sin(s * 13) else flank)
                if fam == belly: lit = lit + .5 - max(0, (v - .85)) * 7
                if fam == back: lit -= .5
                if sc and s > sp.get('head', .22):
                    row = int((yi) // max(1, sc - 1)); cx = (xi + (row % 2) * (sc // 2 + (sc & 1))) % sc
                    if cx == 0: lit -= .85
                    elif cx == 1 and (yi % max(1, sc - 1)) == 0: lit += .8
                col = None
                for m in pats:
                    c = m(self, s, v, xi, yi)
                    if c is not None: col = c
                if col is not None:
                    fam = col[0]; lit = col[1] + (0 if len(col) > 2 else (n - .5) * 1.0)
                self.id[yi, xi] = ci(fam, lit); self.body[yi, xi] = True
    def head(self):
        sp = self.sp; e = sp.get('eye', dict(t=.09, v=.36, r=1)); he = sp.get('head', .22)
        # gill cover
        if sp.get('gill', True):
            for q in np.arange(.08, .92, .012):
                bow = .022 * math.sin(q * math.pi) * sp.get('gillbow', 1); s = he + bow; t, b = self.top(s), self.bot(s); x, y = self.at(s, t - q * (t + b)); xi, yi = int(x), int(y)
                if self.body[yi, xi]:
                    f, r = FAM_OF[self.id[yi, xi]]; self.id[yi, xi] = ci(f, r - 1.2)
        # mouth: a line cut into the snout
        m = sp.get('mouth', ('term', .12))
        kind, ln = m; nv = {'term': .52, 'sub': .78, 'super': .28, 'duck': .55}[kind]; slope = {'term': .25, 'sub': -.1, 'super': .55, 'duck': .05}[kind]
        for q in np.arange(0, ln, .004):
            s = .004 + q; t, b = self.top(s), self.bot(s); v = nv + slope * q / max(ln, .01) * .5; x, y = self.at(s, t - v * (t + b)); xi, yi = int(x), int(y)
            if 0 <= xi < self.S and 0 <= yi < self.S and self.body[yi, xi]: self.id[yi, xi] = ci(sp.get('lip', 'black'), 1)
        if kind == 'duck' and sp.get('teeth'):
            for q in np.arange(.01, ln, ln / 3.5):
                x, y = self.at(.004 + q, self.top(q) - (nv + .14) * (self.top(q) + self.bot(q))); self.plot(x, y, ci('ivory', 5))
        # eye
        s, v, r = e['t'], e['v'], e['r']; t, b = self.top(s), self.bot(s); x, y = self.at(s, t - v * (t + b)); xi, yi = int(x), int(y)
        ring, pupil, glint = e.get('ring', 'gold'), e.get('pupil', ('black', 0)), e.get('glint', ('ivory', 5))
        if e.get('blind'): self.id[yi, xi] = ci(ring, 2); return
        if r == 0:
            self.id[yi, xi] = ci(*pupil)
        elif r == 1:     # small eye: dark 2x2 with a lit corner, pale ring only on the side away from the snout
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)): self.plot(xi + dx, yi + dy, ci(*pupil))
            self.plot(xi, yi, ci(*glint)); self.plot(xi + 2, yi, ci(ring, 3)); self.plot(xi + 2, yi + 1, ci(ring, 2))
        else:            # large eye: round iris, pupil, one glint
            for dx, dy in ((0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2)): self.plot(xi + dx, yi + dy, ci(ring, 4 if dy < 0 else (3 if dy < 2 else 2)))
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)): self.plot(xi + dx, yi + dy, ci(*pupil))
            self.plot(xi, yi, ci(*glint))
    def barbel(self, s, v, length, ang, curl=.08, ramp='flesh', rank=3):
        t, b = self.top(s), self.bot(s); x, y = self.at(s, t - v * (t + b)); a = math.radians(ang)
        for q in range(int(length * 2.5) + 1):
            f = q / (length * 2.5); self.plot(x + math.cos(a + curl * f * 8) * f * length, y + math.sin(a + curl * f * 8) * f * length, ci(ramp, rank - f))
        self.tip = (x + math.cos(a + curl * 8) * length, y + math.sin(a + curl * 8) * length)
    def outline(self):
        a = self.id; m = a != 0; p = np.pad(m, 1); inner = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]; out = a.copy()
        for y, x in zip(*np.where(m & ~inner)):
            f, r = FAM_OF[a[y, x]]; above = y > 0 and not m[y - 1, x]
            out[y, x] = ci(f, min(r, 1) if above else 0) if self.body[y, x] else ci(f, min(r, 1))
        self.id = out
        # lone-pixel clean-up: a pixel unlike all four neighbours by family and rank takes the local majority
        a = self.id.copy()
        for y in range(1, self.S - 1):
            for x in range(1, self.S - 1):
                if a[y, x] == 0: continue
                nb = [a[y - 1, x], a[y + 1, x], a[y, x - 1], a[y, x + 1]]
                if sum(1 for n in nb if n == 0) >= 4: self.id[y, x] = 0
    def finish(self):
        ys, xs = np.where(self.id != 0); x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max(); w, h = x1 - x0 + 1, y1 - y0 + 1
        assert w <= 32 and h <= 32, (self.sp['id'], w, h)
        c = Canvas(32, 32); ox, oy = (32 - w) // 2, (32 - h) // 2; c.a[oy:oy + h, ox:ox + w] = self.id[y0:y1 + 1, x0:x1 + 1]; return c, int(w), int(h)

# ---- markings. Each returns a function (plate, s, v, x, y) -> (family, rank[, flat]) or None
def noise(seed):
    r = random.Random(seed); pts = [(r.random() * 96, r.random() * 96, r.random()) for _ in range(90)]
    def n(x, y): return min(((x - a) ** 2 + (y - b) ** 2, c) for a, b, c in pts)[1]
    return n
def bars(n, fam, r=1, w=.4, v0=0, v1=.72, t0=.24, t1=.97, lean=.0, flat=False):
    def f(p, s, v, x, y):
        if not (t0 < s < t1 and v0 <= v <= v1): return None
        u = (s - lean * v - t0) / (t1 - t0) * n
        if (u % 1) < w * (1 - (v - v0) / (v1 - v0 + .01) * .45): return (fam, r, 1) if flat else (fam, r)
    return f
def stripe(a, b, fam, r=2, t0=0.0, t1=1.0, flat=False):
    def f(p, s, v, x, y):
        if t0 <= s <= t1 and a <= v <= b: return (fam, r, 1) if flat else (fam, r)
    return f
def spots(n, fam, r=1, size=1.2, v0=.05, v1=.75, t0=.2, t1=.97, seed=1, halo=None):
    rng = random.Random(seed); P = [(t0 + rng.random() * (t1 - t0), v0 + rng.random() * (v1 - v0), size * (.7 + rng.random() * .6)) for _ in range(n)]
    def f(p, s, v, x, y):
        for (a, b, z) in P:
            ax, ay = p.at(a, p.top(a) - b * (p.top(a) + p.bot(a))); d = math.hypot(x + .5 - ax, y + .5 - ay)
            if d <= z: return (fam, r, 1)
            if halo and d <= z + 1: return (halo, 4, 1)
    return f
def ocellus(t, vv, z, ring, centre):
    def f(p, s, v, x, y):
        ax, ay = p.at(t, p.top(t) - vv * (p.top(t) + p.bot(t))); d = math.hypot(x + .5 - ax, y + .5 - ay)
        if d <= z * .55: return (centre[0], centre[1], 1)
        if d <= z: return (ring[0], ring[1], 1)
    return f
def mottle(fam, r=1, thresh=.5, seed=3, v1=.8, t0=.15, t1=1.0, scale=1):
    n = noise(seed)
    def f(p, s, v, x, y):
        if t0 < s < t1 and v < v1 and n(x * scale, y * scale) < thresh: return (fam, r)
    return f
def speckle(fam, r=4, step=3, v0=.05, v1=.8, t0=.2, t1=1.0):
    def f(p, s, v, x, y):
        if t0 < s < t1 and v0 < v < v1 and (x * 7 + y * 13) % (step * 5) == 0: return (fam, r, 1)
    return f
def worm(fam, r=1, seed=1, freq=.9, v1=.55, t0=.2, t1=1.0):
    def f(p, s, v, x, y):
        if t0 < s < t1 and v < v1 and abs(math.sin(x * freq + 2.3 * math.sin(y * .7 + seed))) < .24: return (fam, r)
    return f
def region(t0, t1, fam, r=None, v0=0, v1=1, flat=False):
    def f(p, s, v, x, y):
        if t0 <= s <= t1 and v0 <= v <= v1: return (fam, r if r is not None else 3, 1) if flat else (fam, r if r is not None else 3)
    return f
def glowline(fam, vv, gap=3, t0=.2, t1=.96, r=5):
    def f(p, s, v, x, y):
        if t0 < s < t1 and abs(v - vv) < .06 and x % gap == 0: return (fam, r, 1)
    return f
def lateral(vv, fam='black', r=2, dash=2, t0=.22, t1=.98, curvy=0):
    def f(p, s, v, x, y):
        if t0 < s < t1 and abs(v - (vv + curvy * math.sin(s * 3.14))) < .035 and x % dash != 0: return (fam, r, 1)
    return f
def ribs(fam='bone', r=4, gap=3, t0=.25, t1=.85, v0=.25, v1=.72):
    def f(p, s, v, x, y):
        if t0 < s < t1 and v0 < v < v1 and x % gap == 0: return (fam, r, 1)
    return f

def render(sp):
    # the plate is a hard 32 px bound: long bodies shrink a pixel at a time, keeping their proportions
    while True:
        try: return _render(sp)
        except AssertionError as e:
            if not sp.get('fit') or sp['L'] < 7 or e.args[0][1] <= 32: raise
            sp['L'] -= 1; sp['spine'] = straight(sp['L'], sp['arch'])
def _render(sp):
    p = Plate(sp)
    for fn in sp.get('behind', []): fn(p)
    p.draw_body()
    for fn in sp.get('over', []): fn(p)
    p.head()
    for fn in sp.get('last', []): fn(p)
    p.outline(); return p.finish()
def pal_rgba(c): return np.dstack([np.array(PALETTE, dtype=np.uint8)[c.a], (c.a != 0).astype(np.uint8) * 255])
