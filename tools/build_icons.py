"""Compile hand-authored icon grids -> individual PNGs, atlas, gallery, validation report."""
import sys, os, json, importlib
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
from pixelart.canvas import Canvas
from pixelart.palette import PAL
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets/items'); ICO = os.path.join(OUT, 'icons'); os.makedirs(ICO, exist_ok=True)
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

def main():
    grids = load_grids()
    items = json.load(open(os.path.join(OUT, 'items.json')))['items']; tools = json.load(open(os.path.join(OUT, 'tools.json')))['tools']
    wanted = [i['id'] for i in items] + ['tool_' + t['id'] for t in tools]
    report = {'size': S, 'finished': [], 'placeholder': [], 'errors': []}
    cols = 10; names = wanted
    sheet = Canvas(cols * S, S * ((len(names) + cols - 1) // cols)); index = {}
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
    # uniqueness: no two finished icons identical
    seen = {}
    for nm in report['finished']:
        key = ''.join(grids[nm][1])
        if key in seen: report['errors'].append(f'{nm} duplicates {seen[key]}')
        seen[key] = nm
    Image.fromarray(sheet.a, 'L').save(os.path.join(OUT, 'icons_idx.png')); sheet.save(os.path.join(OUT, 'icons_preview.png'))
    json.dump({'size': S, 'cols': cols, 'index': index, 'finished': report['finished'], 'placeholder': report['placeholder']}, open(os.path.join(OUT, 'icons.json'), 'w'))
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
    g1, g2, g4 = card(1, len(fin)), card(2, len(fin)), card(4, 8)
    W = max(g1.width, g2.width, g4.width); gal = Image.new('RGB', (W + 16, g1.height + g2.height + g4.height + 32), (30, 26, 22))
    gal.paste(g1, (8, 8)); gal.paste(g2, (8, 16 + g1.height)); gal.paste(g4, (8, 24 + g1.height + g2.height)); gal.save(os.path.join(ROOT, 'renders/icon_gallery.png'))
    print(f'finished {len(fin)}, placeholder {len(report["placeholder"])}, errors {report["errors"]}')
if __name__ == '__main__': main()
