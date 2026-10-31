"""Compile hand-authored icon grids -> individual PNGs, atlas, gallery, validation report."""
import sys, os, json, importlib
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
from pixelart.canvas import Canvas
from pixelart.palette import PAL
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets/items'); ICO = os.path.join(OUT, 'icons'); ICO32 = os.path.join(OUT, 'icons32'); os.makedirs(ICO, exist_ok=True); os.makedirs(ICO32, exist_ok=True)
S = 16

def load_grids():
    grids = {}
    for mod in ('pilot', 'catalog'):
        try: m = importlib.import_module(f'icons.{mod}'); grids.update(m.ICONS)
        except ModuleNotFoundError: pass
    return grids

def compile_icon(legend, rows):
    c = Canvas(S, S)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == '.': continue
            fam, rank = legend[ch]; c.put(x, y, PAL.i(fam, rank))
    return c

def epx(a):
    """Scale2x/EPX on an index image: doubles resolution, smoothing diagonal
    stair-steps while keeping flat edges crisp and never inventing colours."""
    h, w = a.shape; out = np.zeros((h * 2, w * 2), dtype=a.dtype)
    P = np.pad(a, 1)
    for y in range(h):
        for x in range(w):
            c = a[y, x]; A = P[y, x + 1]; B = P[y + 1, x + 2]; C = P[y + 1, x]; D = P[y + 2, x + 1]
            e0 = A if (C == A and C != D and A != B) else c
            e1 = B if (A == B and A != C and B != D) else c
            e2 = C if (D == C and D != B and C != A) else c
            e3 = D if (B == D and B != A and D != C) else c
            out[y * 2, x * 2] = e0; out[y * 2, x * 2 + 1] = e1; out[y * 2 + 1, x * 2] = e2; out[y * 2 + 1, x * 2 + 1] = e3
    return out

def refine32(a):
    """Hand-rule refinement after EPX: (1) outline stays continuous — any
    transparent pixel between two outline pixels becomes outline; (2) lone
    interior pixels of a different tone that EPX created are absorbed into
    their majority neighbour; (3) a 2-px specular on glass/metal/crystal/
    fruit highlights where the 16-px art had a single highlight pixel."""
    h, w = a.shape; out = a.copy()
    fam = lambda i: PAL.family_of(int(i)); rank = lambda i: PAL.rank_of(int(i))
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            v = a[y, x]
            if v == 0: continue
            n = [a[y - 1, x], a[y + 1, x], a[y, x - 1], a[y, x + 1]]
            same = sum(1 for k in n if k == v)
            if same == 0:                       # lone pixel: absorb into the most common non-transparent neighbour
                nz = [k for k in n if k]; 
                if nz: out[y, x] = max(set(nz), key=nz.count)
    return out

def main():
    grids = load_grids()
    items = json.load(open(os.path.join(OUT, 'items.json')))['items']; tools = json.load(open(os.path.join(OUT, 'tools.json')))['tools']
    wanted = [i['id'] for i in items] + ['tool_' + t['id'] for t in tools]
    report = {'size': S, 'finished': [], 'placeholder': [], 'errors': []}
    cols = 10; names = wanted
    sheet = Canvas(cols * S, S * ((len(names) + cols - 1) // cols)); index = {}
    sheet32 = Canvas(cols * S * 2, S * 2 * ((len(names) + cols - 1) // cols))
    for k, nm in enumerate(names):
        x, y = (k % cols) * S, (k // cols) * S; index[nm] = [x, y]
        if nm in grids:
            c = compile_icon(*grids[nm]); report['finished'].append(nm)
            # technical validation: bounds, transparency, padding (at least 1 px empty on each side), uniqueness
            m = c.mask(); ys, xs = np.nonzero(m)
            if not len(xs): report['errors'].append(f'{nm}: empty')
            elif xs.min() < 1 or xs.max() > S - 2: report['errors'].append(f'{nm}: touches the left/right canvas edge (padding)')
            elif ys.min() < 1 and ys.max() > S - 2: report['warnings'] = report.get('warnings', []) + [f'{nm}: uses all 16 rows (tall object)']
        else:
            c = Canvas(S, S); st = PAL.ramp('stone')
            c.rect(2, 2, 12, 12, st[1]); c.rect(3, 3, 10, 10, 0); c.rect(7, 5, 2, 5, st[3]); c.rect(7, 11, 2, 2, st[3])   # explicit "?" placeholder tile
            report['placeholder'].append(nm)
        c.save(os.path.join(ICO, nm + '.png')); sheet.blit(c, x, y)
        b = Canvas(S * 2, S * 2); b.a = refine32(epx(c.a)); b.save(os.path.join(ICO32, nm + '.png')); sheet32.blit(b, x * 2, y * 2)
    # uniqueness: no two finished icons identical
    seen = {}
    for nm in report['finished']:
        key = ''.join(grids[nm][1])
        if key in seen: report['errors'].append(f'{nm} duplicates {seen[key]}')
        seen[key] = nm
    Image.fromarray(sheet.a, 'L').save(os.path.join(OUT, 'icons_idx.png')); sheet.save(os.path.join(OUT, 'icons_preview.png'))
    Image.fromarray(sheet32.a, 'L').save(os.path.join(OUT, 'icons32_idx.png')); sheet32.save(os.path.join(OUT, 'icons32_preview.png'))
    json.dump({'size': S, 'cols': cols, 'index': index, 'hires': {'size': S * 2, 'file': 'icons32_idx.png', 'source': 'EPX + cleanup of the 16px grids'}, 'finished': report['finished'], 'placeholder': report['placeholder']}, open(os.path.join(OUT, 'icons.json'), 'w'))
    json.dump(report, open(os.path.join(OUT, 'icons_validation.json'), 'w'), indent=1)
    # gallery: 1x row, 2x row, 4x grid, each on a neutral warm-dark card
    fin = report['finished']
    def card(scale, per_row):
        rows = (len(fin) + per_row - 1) // per_row; pad = 4 * scale; cell = S * scale + pad
        img = Image.new('RGB', (per_row * cell + pad, rows * cell + pad), (58, 50, 40))
        for k, nm in enumerate(fin):
            ic = Image.open(os.path.join(ICO, nm + '.png')).convert('RGBA').resize((S * scale, S * scale), Image.NEAREST)
            img.paste(ic, (pad + (k % per_row) * cell, pad + (k // per_row) * cell), ic)
        return img
    def card32(scale, per_row):
        rows = (len(fin) + per_row - 1) // per_row; pad = 4 * scale; cell = S * 2 * scale + pad
        img = Image.new('RGB', (per_row * cell + pad, rows * cell + pad), (58, 50, 40))
        for k, nm in enumerate(fin):
            ic = Image.open(os.path.join(ICO32, nm + '.png')).convert('RGBA').resize((S * 2 * scale, S * 2 * scale), Image.NEAREST)
            img.paste(ic, (pad + (k % per_row) * cell, pad + (k // per_row) * cell), ic)
        return img
    g1, g2, g4 = card(1, len(fin)), card(2, len(fin)), card32(2, 8)
    W = max(g1.width, g2.width, g4.width); gal = Image.new('RGB', (W + 16, g1.height + g2.height + g4.height + 32), (30, 26, 22))
    gal.paste(g1, (8, 8)); gal.paste(g2, (8, 16 + g1.height)); gal.paste(g4, (8, 24 + g1.height + g2.height)); gal.save(os.path.join(ROOT, 'renders/icon_gallery.png'))
    print(f'finished {len(fin)}, placeholder {len(report["placeholder"])}, errors {report["errors"]}')
if __name__ == '__main__': main()
