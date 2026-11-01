"""Adopted PixelLab art. Each source is cut out, cleaned of baked ground, and mapped onto *chosen* world palette
families, so day, night and season tables keep working (an oak canopy stays in the 'oak' ramp and still turns in autumn).
Sprites keep their library names, so composition, collision and tests keep working unchanged."""
from __future__ import annotations
import os, json, copy
import numpy as np
from PIL import Image
from .canvas import Canvas
from .palette import PAL
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); SRC = os.path.join(ROOT, 'assets/third_party/pixellab')
def label(m):
    """4-connected labelling, kept here so the art build needs only numpy."""
    lab = np.zeros(m.shape, dtype=np.int32); n = 0; h, w = m.shape
    for y0, x0 in zip(*np.nonzero(m)):
        if lab[y0, x0]: continue
        n += 1; lab[y0, x0] = n; st = [(y0, x0)]
        while st:
            y, x = st.pop()
            for a, b in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= a < h and 0 <= b < w and m[a, b] and not lab[a, b]: lab[a, b] = n; st.append((a, b))
    return lab, n
def dilate(m, it=2):
    for _ in range(it):
        p = np.pad(m, 1); m = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return m
def rgba(name):
    p = os.path.join(SRC, name + '.png')
    return np.array(Image.open(p).convert('RGBA')) if os.path.exists(p) else None
def components(a, min_px=30):
    """Cut a sheet into its separate objects, reading order. Small crumbs join their nearest neighbour by dilation."""
    m = a[:, :, 3] > 128; lab, n = label(dilate(m)); out = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero((lab == i) & m)
        if len(xs) < min_px: continue
        out.append((ys.min() // 40, xs.min(), a[ys.min():ys.max() + 1, xs.min():xs.max() + 1].copy() * ((lab[ys.min():ys.max() + 1, xs.min():xs.max() + 1] == i)[:, :, None])))
    return [o[2] for o in sorted(out, key=lambda o: (o[0], o[1]))]
def trim(a):
    ys, xs = np.nonzero(a[:, :, 3] > 128); return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
def shrink(a, w):
    """Scale down to w px wide by taking the commonest colour in each block: clusters survive, no blur, no new colours."""
    H, W = a.shape[:2]
    if w >= W: return a
    f = W / w; h = max(1, round(H / f)); out = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            b = a[int(y * f):max(int(y * f) + 1, int((y + 1) * f)), int(x * f):max(int(x * f) + 1, int((x + 1) * f))].reshape(-1, 4)
            op = b[b[:, 3] > 128]
            if len(op) * 2 < len(b): continue
            q = (op[:, :3] // 24); k = q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2]; vals, cnt = np.unique(k, return_counts=True); sel = op[k == vals[cnt.argmax()]]; out[y, x] = list(sel.mean(0).astype(np.uint8)[:3]) + [255]
    return out
def strip_ground(a, frac=.22, test=None):
    """Remove the flat patch of grass, soil or shadow the generator baked under a subject."""
    h = a.shape[0]; y0 = int(h * (1 - frac)); r, g, b = [a[:, :, i].astype(int) for i in range(3)]
    t = (g > r + 8) & (g > b) if test is None else test(r, g, b); a = a.copy(); a[y0:, :, 3][t[y0:]] = 0; return keep_largest(a)
def keep_largest(a):
    lab, n = label(a[:, :, 3] > 128)
    if n < 2: return trim(a)
    big = np.bincount(lab.ravel())[1:].argmax() + 1; a = a.copy(); a[lab != big, 3] = 0; return trim(a)
def to_families(a, fams, gain=1.0, lift=0, sat=1.0):
    """Nearest colour among the named ramps, measured with luma weighted, so ramps stay ramps. Half-steps are included."""
    idxs = []
    for f in fams:
        idxs += [PAL.index[(f, r)] for r in range(len(PAL.ramp(f)))]
        if f + '~' in {e[0] for e in PAL.entries}: idxs += [PAL.index[(f + '~', r)] for r in range(len(PAL.ramp(f)) - 1)]
    pal = np.array([PAL.day[i] for i in idxs], dtype=float); rgb = a[:, :, :3].astype(float); L = rgb @ [.3, .59, .11]; rgb = L[:, :, None] + (rgb - L[:, :, None]) * sat; rgb = np.clip(rgb * gain + lift, 0, 255)
    w = np.array([.8, 1.2, .7]); d = (((rgb[:, :, None, :] - pal[None, None]) * w) ** 2).sum(3); c = Canvas(a.shape[1], a.shape[0]); c.a = np.array(idxs, dtype=np.uint8)[d.argmin(2)]; c.a[a[:, :, 3] < 128] = 0; return c
def regions(a, rules, **kw):
    """Map parts of a sprite to different ramps by what they are, so a leaf never lands on a bark ramp and a flame never on a tent."""
    r, g, b = [a[:, :, i].astype(int) for i in range(3)]; c = Canvas(a.shape[1], a.shape[0]); done = np.zeros(a.shape[:2], bool)
    for test, fams in rules:
        m = (test(r, g, b) if test else np.ones_like(done)) & ~done; part = to_families(a, fams, **kw); c.a[m] = part.a[m]; done |= m
    c.a[a[:, :, 3] < 128] = 0; return c
GREEN = lambda r, g, b: g > r + 2
def bare(c, fam, rng_seed=3, bark=None):
    """Winter deciduous from the same drawing: the generated trunk stays, the canopy goes, limbs grow in the trunk's own colours."""
    import random
    rng = random.Random(rng_seed); ramp = PAL.ramp(fam); out = Canvas(c.w, c.h); leaf = set(PAL.ramp('oak') + PAL.ramp('oak_b') + PAL.ramp('birch') + PAL.ramp('rowan') + PAL.ramp('berry'))
    keep = ~np.isin(c.a, list(leaf)) & (c.a != 0); lab, n = label(keep)
    if n > 1: keep = lab == (np.bincount(lab.ravel())[1:].argmax() + 1)   # stray bark-coloured flecks from the canopy go with it
    out.a[keep] = c.a[keep]
    ys, xs = np.nonzero(keep); top = ys.min() if len(ys) else c.h // 2; tx = int(np.median(xs[ys <= top + 2])) if len(xs) else c.w // 2; hi = ramp[min(len(ramp) - 1, 3)]; lo = ramp[1]; sn = PAL.ramp('snow')
    def limb(x, y, a, L, w):
        for t in range(L):
            x += np.cos(a); y += np.sin(a); a += rng.uniform(-.14, .14)
            for k in range(w):
                out.put(int(x) + k, int(y), lo if k else hi)
            if t % 3 == 0 and w == 1: out.put(int(x), int(y) - 1, sn[3])
        if w > 1 or L > 7:
            for d in (-.55, .5):
                if y > 2: limb(x, y, a + d + rng.uniform(-.1, .1), max(4, int(L * .68)), max(1, w - 1))
    for a0 in (-1.57, -2.3, -.85): limb(tx, top + 1, a0, max(10, top // 3), 3 if a0 == -1.57 else 2)
    return out
def pine_snow(c):
    out = snowcap(c, 2); pr = PAL.ramp('pine'); sn = PAL.ramp('snow'); up = np.roll(c.a, 1, 0)
    for r, col in ((5, sn[4]), (4, sn[3]), (3, sn[2])):
        out.a[(c.a == pr[r])] = col
    return out
def extend(c, w):
    """Lengthen a bridge by repeating its middle span."""
    if w <= c.w: return c
    mid = c.w // 2; span = 8; out = Canvas(w, c.h); out.a[:, :mid] = c.a[:, :mid]; out.a[:, w - (c.w - mid):] = c.a[:, mid:]
    for x in range(mid, w - (c.w - mid)): out.a[:, x] = c.a[:, mid - span + (x - mid) % span]
    return out
def pier():
    """A straight east-facing pier, hand-drawn: generated docks came on a baked slab in another projection."""
    from .palette import PAL as P
    g = P.ramp('wood_grey'); w = P.ramp('wood'); c = Canvas(70, 30)
    for x in range(0, 66):
        pl = x // 5; k = 3 - (pl * 7 % 3 == 0); c.vline(x, 4, 21, g[k] if x % 5 else g[0])
        if pl * 3 % 4 == 0 and x % 5 == 2: c.put(x, 9 + pl % 7, g[1])
    c.hline(0, 65, 4, g[4]); c.hline(0, 65, 21, g[1]); c.rect(0, 22, 66, 2, g[0])
    for x in (2, 22, 42, 62):
        c.rect(x, 22, 3, 7, w[1]); c.vline(x, 22, 28, w[2]); c.hline(x - 1, x + 3, 28, P.ramp('water')[5])
    for x, y in ((0, 0), (62, 0)):
        c.rect(x, y, 4, 8, w[2]); c.vline(x, y, y + 7, w[4]); c.hline(x, x + 3, y, w[5])
    return c
def snowcap(c, depth=3):
    """Winter from the same drawing: snow on whatever faces the sky, never a second art style."""
    out = c.copy(); sn = PAL.ramp('snow'); h, w = c.a.shape
    for x in range(w):
        ys = np.nonzero(c.a[:, x])[0]
        if not len(ys): continue
        t = ys[0]; run = depth - (1 if (x * 7) % 5 == 0 else 0)
        for k in range(run):
            if t + k < h and c.a[t + k, x]: out.a[t + k, x] = sn[4 if k == 0 else 3 if k == 1 else 2]
        for y in ys[1:]:      # ledges
            if c.a[y - 1, x] == 0: out.a[y, x] = sn[3]
    return out
def base_x(c):
    ys, xs = np.nonzero(c.a); low = xs[ys >= ys.max() - max(2, c.h // 10)]; return int(np.median(low)), int(ys.max())
def adopt(lib, name, c, base=None, shadow=None, **over):
    old = lib.get(name); s = copy.copy(old) if old else None
    if s is None: return
    s.c = c; x, y = base_x(c); s.ox = base[0] if base else x; s.oy = base[1] if base else max(0, y - 1)
    if shadow is not None: s.shadow = shadow
    elif s.shadow: s.shadow = (max(3, int(c.w * .36)), max(1, s.shadow[1]), s.shadow[2], s.shadow[3])
    for k, v in over.items(): setattr(s, k, v)
    lib[name] = s
ADOPTED = []
def apply(lib):
    def single(src, names, fams, ground=True, flip=False, **kw):
        a = rgba(src)
        if a is None: return
        a = trim(a); a = strip_ground(a) if ground else a; c = to_families(a, fams, **kw)
        if flip: c.a = c.a[:, ::-1]
        for n in names: adopt(lib, n, c)
        ADOPTED.extend(names)
    def tree(src, name, leaf, bark=('wood',), **kw):
        a = rgba(src)
        if a is None: return
        a = strip_ground(trim(a)); adopt(lib, name, regions(a, [(GREEN, leaf), (None, list(bark))], **kw)); ADOPTED.append(name)
    tree('a_oak_1', 'oak_0', ['oak']); tree('b_oak_2', 'oak_1', ['oak_b']); tree('b_oak_3', 'oak_2', ['oak']); tree('b_oak_4', 'oak_3', ['oak_b'])
    tree('b_birch_1', 'birch_0', ['birch'], ('bark_birch',)); tree('b_birch_2', 'birch_1', ['birch'], ('bark_birch',)); tree('b_pine_1', 'pine_0', ['pine']); tree('b_pine_2', 'pine_1', ['pine'])
    a = rgba('b_willow')
    if a is not None:
        a = strip_ground(trim(a)); c = regions(a, [(GREEN, ['oak']), (None, ['wood'])])
        for n in ('willow_0', 'willow_1'): adopt(lib, n, c); ADOPTED.append(n)
    a = rgba('b_rowan')
    if a is not None:
        a = strip_ground(trim(a)); c = regions(a, [(lambda r, g, b: r > g + 50, ['berry']), (GREEN, ['rowan']), (None, ['wood'])], gain=1.35, lift=10)
        for n in ('rowan_0', 'rowan_1'): adopt(lib, n, c); ADOPTED.append(n)
    # camp: the tent interior goes to the emissive family so it still glows at night
    a = rgba('a_tent_1')
    if a is not None:
        a = trim(a); c = regions(a, [(lambda r, g, b: (r < 80) & (np.arange(a.shape[0])[:, None] > a.shape[0] * .34) & (np.abs(np.arange(a.shape[1])[None, :] - a.shape[1] * .47) < a.shape[1] * .2), ['tent_interior']), (None, ['canvas', 'wood', 'rope', 'dirt'])]); adopt(lib, 'tent', c); ADOPTED.append('tent')
        adopt(lib, 'tent_winter', snowcap(c, 4))
    a = rgba('a_fire_1')
    if a is not None:
        a = shrink(trim(a), 38); c = regions(a, [(lambda r, g, b: (r > 190) & (b < 130) & (r > g + 20), ['fire']), (lambda r, g, b: (r > g + 12), ['wood']), (None, ['stone'])]); adopt(lib, 'campfire', c); ADOPTED.append('campfire')
        fire = np.isin(c.a, PAL.ramp('fire')); u = c.copy(); u.a[fire] = 0; adopt(lib, 'campfire_unlit', u); e = c.copy(); e.a[fire] = PAL.ramp('ember')[1]; adopt(lib, 'campfire_embers', e)
    # sheets
    def sheet(src, names, fams, order=None, ground=None, widths=None, **kw):
        a = rgba(src)
        if a is None: return []
        cs = components(a)
        if order: cs = sorted(cs, key=order)
        for i, (n, co) in enumerate(zip(names, cs)):
            co = trim(co); co = strip_ground(co, *(ground or ())) if ground is not None else co
            if widths: co = shrink(co, widths[i % len(widths)])
            adopt(lib, n, to_families(co, fams, **kw)); ADOPTED.append(n)
        return cs
    big = lambda o: -(o[:, :, 3] > 128).sum()
    sheet('c_rocks_round' if rgba('c_rocks_round') is not None else 'a_rocks_1', ['boulder_l0', 'boulder_l1', 'boulder_m0', 'boulder_m1', 'boulder_s0', 'boulder_s1'], ['stone', 'pebble'], order=big, widths=[40, 38, 28, 26, 18, 16], gain=1.0 if rgba('c_rocks_round') is not None else 1.75, lift=0 if rgba('c_rocks_round') is not None else 14)
    sheet('b_rocks_mossy', ['boulder_mossy_l0', 'boulder_mossy_l1', 'boulder_mossy_m0', 'boulder_mossy_m1'], ['stone', 'moss'], order=big, ground=(.25,), widths=[40, 36, 28, 26], gain=1.1)
    sheet('c_shrubs_side' if rgba('c_shrubs_side') is not None else 'b_shrubs', ['shrub_0', 'shrub_1', 'shrub_2', 'shrub_3b', 'hedge_0', 'hedge_1'], ['shrub', 'berry'], ground=(.24, lambda r, g, b: r > g), widths=[28, 26, 24, 30, 28, 26])
    sheet('c_ferns_clean' if rgba('c_ferns_clean') is not None else 'b_ferns', ['fern_0', 'fern_1', 'fern_2'], ['fern', 'grass'], order=big, widths=[26, 22, 20])
    fl = 'c_flowers_clean' if rgba('c_flowers_clean') is not None else 'b_flowers'
    sheet(fl, ['flowers_w0', 'flowers_y0', 'flowers_b0', 'flowers_p0', 'flowers_r0', 'flowers_b1'], ['flower_w', 'flower_y', 'flower_b', 'flower_p', 'berry', 'grass'], widths=[11, 9, 9, 10, 9, 9], ground=(.28, lambda r, g, b: (b > g) | (r < 80)))
    for dup, src_ in (('flowers_w1', 'flowers_w0'), ('flowers_y1', 'flowers_y0'), ('flowers_p1', 'flowers_p0'), ('flowers_r1', 'flowers_r0')):
        if src_ in ADOPTED: lib[dup] = copy.copy(lib[src_]); lib[dup].name = dup; lib[dup].c = lib[src_].c.copy(); lib[dup].c.a = lib[dup].c.a[:, ::-1].copy()
    sheet('b_reeds', ['reeds_0', 'reeds_1', 'lily_0', 'lily_1'], ['reed', 'lily', 'flower_p', 'wood'], ground=(.3, lambda r, g, b: (r > g) & (b < 90)), widths=[22, 22, 16, 16])
    logs = rgba('b_logs')
    if logs is not None:
        cs = components(logs); cs = sorted(cs, key=lambda o: (o.shape[1] > o.shape[0] * 1.5, o.shape[1]))   # stump, stack, then long logs
        for n, co, w in zip(['woodpile', 'stump_0', 'log_seat', 'hollowlog_0'], cs, [26, 20, 26, 46]): adopt(lib, n, to_families(shrink(trim(co), w), ['wood', 'moss', 'canvas'])); ADOPTED.append(n)
    sheet('b_mushrooms', ['shroom_0', 'shroom_1'], ['shroom', 'shroom_stem'], widths=[11, 10])
    sheet('b_rubble', ['rubble_0', 'rubble_1'], ['rubble', 'ruin', 'moss'], order=big, widths=[32, 28])
    a = rgba('b_lantern')
    if a is not None:
        a = trim(a); adopt(lib, 'lantern_post', regions(a, [(lambda r, g, b: (r > 215) & (g > 160) & (b < 170), ['lantern_glass']), (lambda r, g, b: np.abs(r - b) < 26, ['metal']), (None, ['wood'])])); ADOPTED.append('lantern_post')
    adopt(lib, 'dock', pier(), base=(2, 24)); ADOPTED.append('dock')
    a = rgba('b_ruin_1')         # the arch keeps its doorway, which the collision map already leaves open
    if a is not None: adopt(lib, 'ruin_back', to_families(trim(a), ['ruin', 'moss', 'oak']), base=None); ADOPTED.append('ruin_back')
    a = rgba('b_ruin_2')
    if a is not None: adopt(lib, 'ruin_side', to_families(trim(a), ['ruin', 'moss', 'oak'])); ADOPTED.append('ruin_side')
    # winter from the same drawing
    for n in ('boulder_l0', 'boulder_l1', 'boulder_m0', 'boulder_m1', 'boulder_s0', 'boulder_s1', 'boulder_mossy_l0', 'boulder_mossy_l1', 'boulder_mossy_m0', 'boulder_mossy_m1', 'ruin_back', 'ruin_side', 'rubble_0', 'rubble_1', 'stump_0', 'dock', 'shrub_0', 'shrub_1', 'shrub_2', 'shrub_3b', 'hedge_0', 'hedge_1', 'fern_0', 'fern_1', 'fern_2', 'reeds_0', 'reeds_1', 'woodpile', 'log_seat', 'hollowlog_0', 'lantern_post', 'campfire', 'campfire_unlit'):
        if n in ADOPTED or n in lib:
            wn = n + '_winter'; lib[wn] = copy.copy(lib[n]); lib[wn].name = wn; cc = snowcap(lib[n].c)
            if n == 'campfire': f = np.isin(lib[n].c.a, PAL.ramp('fire') + PAL.ramp('ember')); cc.a[f] = lib[n].c.a[f]
            lib[wn].c = cc
    for n, fam in (('oak_0', 'wood'), ('oak_1', 'wood'), ('oak_2', 'wood'), ('oak_3', 'wood'), ('birch_0', 'bark_birch'), ('birch_1', 'bark_birch'), ('willow_0', 'wood'), ('willow_1', 'wood')):
        if n in ADOPTED: wn = n + '_winter'; lib[wn] = copy.copy(lib[n]); lib[wn].name = wn; lib[wn].c = bare(lib[n].c, fam, len(n) + int(n[-1]) * 5)
    for n in ('pine_0', 'pine_1'):
        if n in ADOPTED: wn = n + '_winter'; lib[wn] = copy.copy(lib[n]); lib[wn].name = wn; lib[wn].c = pine_snow(lib[n].c)
    w = rgba('c_wall_long')
    if w is not None:
        from .objects import Sprite
        w = strip_ground(trim(w), .14); c = to_families(shrink(w, 92), ['ruin', 'moss', 'oak']); x, y = base_x(c); lib['ruin_wall'] = Sprite('ruin_wall', c, c.w // 2, c.h - 2, shadow=(40, 3, 3, 1), tags=('structure', 'ysort')); lib['ruin_wall_winter'] = copy.copy(lib['ruin_wall']); lib['ruin_wall_winter'].name = 'ruin_wall_winter'; lib['ruin_wall_winter'].c = snowcap(c)
    b = lib.get('bridge')
    br = rgba('b_bridge')
    if br is not None:
        from .objects import Sprite
        br = trim(br); br = strip_ground(br, .3, lambda r, g, b: np.abs(r - b) < 34); c = extend(to_families(br, ['wood']), 118); lib['bridge'] = Sprite('bridge', c, c.w // 2, c.h - 3, shadow=None, tags=('structure', 'ysort'))
        lib['bridge_winter'] = copy.copy(lib['bridge']); lib['bridge_winter'].name = 'bridge_winter'; lib['bridge_winter'].c = snowcap(c, 2)
    return lib
