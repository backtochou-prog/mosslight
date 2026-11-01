"""Fish plates: atlas, palette, galleries. Add `pilot` to render only the twelve."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image, ImageDraw
from pixelart.fish import render, pal_rgba, PALETTE
from pixelart.fish_species import SPECIES, PILOTS
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(ROOT, 'assets/fishing'); os.makedirs(OUT, exist_ok=True)
def gallery(names, path, cols, scale=4):
    rows = (len(names) + cols - 1) // cols; W, H = cols * (32 * scale + 44), rows * (32 * scale + 22)
    im = Image.new('RGB', (W, H), (232, 222, 196)); d = ImageDraw.Draw(im)
    for i, n in enumerate(names):
        c = plates[n][0]; a = Image.fromarray(pal_rgba(c), 'RGBA'); x, y = (i % cols) * (32 * scale + 44), (i // cols) * (32 * scale + 22)
        im.paste(a, (x + 4, y + 4), a); b = a.resize((32 * scale, 32 * scale), Image.NEAREST); im.paste(b, (x + 40, y + 2), b); d.text((x + 40, y + 32 * scale + 4), n, fill=(70, 50, 30))
    im.save(path)
pilot = 'pilot' in sys.argv
names = PILOTS if pilot else list(SPECIES); plates = {}; bad = []
for n in names:
    try: plates[n] = render(SPECIES[n])
    except AssertionError as e: bad.append(e.args[0])
if bad: print('OVERSIZE', bad); sys.exit(1)
gallery(PILOTS, os.path.join(ROOT, 'renders/fish_pilots.png'), 4)
if not pilot:
    cols = 10; sheet = np.zeros((((len(names) + cols - 1) // cols) * 32, cols * 32), dtype=np.uint8); idx = {}
    for i, n in enumerate(names): x, y = (i % cols) * 32, (i // cols) * 32; sheet[y:y + 32, x:x + 32] = plates[n][0].a; idx[n] = dict(x=x, y=y, w=plates[n][1], h=plates[n][2])
    Image.fromarray(sheet, 'L').save(os.path.join(OUT, 'fish_idx.png')); json.dump(dict(cell=32, cols=cols, palette=PALETTE, index=idx), open(os.path.join(OUT, 'fish_atlas.json'), 'w'))
    for k in range(0, len(names), 20): gallery(names[k:k + 20], os.path.join(ROOT, f'renders/fish_catalog_{k // 20 + 1}.png'), 5, 3)
if not pilot:   # honest distinctness report: silhouette overlap and colour overlap between every pair
    from itertools import combinations
    def feat(c): return c.a != 0, np.bincount(c.a.ravel(), minlength=256)[1:] / max(1, (c.a != 0).sum())
    F_ = {n: feat(plates[n][0]) for n in names}; rep = []
    for a, b in combinations(names, 2):
        ma, ha = F_[a]; mb, hb = F_[b]; iou = (ma & mb).sum() / (ma | mb).sum(); col = np.minimum(ha, hb).sum(); rep.append((round(float(iou), 2), round(float(col), 2), a, b))
    rep.sort(key=lambda r: -(r[0] + r[1])); json.dump(dict(species=len(names), identical_colour_and_shape=[r for r in rep if r[0] > .9 and r[1] > .6], closest=rep[:10]), open(os.path.join(OUT, 'fish_art_report.json'), 'w'), indent=0); print('closest pairs', rep[:5])
    # one sheet at true inventory size: what the player actually sees in the pack
    cols = 15; im = Image.new('RGB', (cols * 34, ((len(names) + cols - 1) // cols) * 34), (40, 34, 26))
    for i, n in enumerate(names): a = Image.fromarray(pal_rgba(plates[n][0]), 'RGBA'); im.paste(a, ((i % cols) * 34 + 1, (i // cols) * 34 + 1), a)
    im.resize((im.width * 3, im.height * 3), Image.NEAREST).save(os.path.join(ROOT, 'renders/fish_all_inventory_size_x3.png'))
print(len(plates), 'plates')
