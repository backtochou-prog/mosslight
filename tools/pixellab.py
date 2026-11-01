"""PixelLab client for MOSSlight. Key comes from PIXL_API_KEY or ~/.config/mosslight/pixellab.env, never the repo.
  python3 tools/pixellab.py balance
  python3 tools/pixellab.py image "a mossy stone lantern" --size 48 --name stone_lantern
Writes assets/third_party/pixellab/<name>_raw.png, <name>_idx.png (world palette indices) and a provenance entry."""
import sys, os, json, base64, io, argparse, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(ROOT, 'assets/third_party/pixellab'); BASE = 'https://api.pixellab.ai/v2'
def key():
    k = os.environ.get('PIXL_API_KEY')
    if k: return k
    p = os.path.expanduser('~/.config/mosslight/pixellab.env')
    if os.path.exists(p):
        for l in open(p):
            if l.startswith('PIXL_API_KEY='): return l.split('=', 1)[1].strip()
    sys.exit('No key: set PIXL_API_KEY in the environment settings.')
def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, headers={'Authorization': 'Bearer ' + key(), 'Content-Type': 'application/json', 'User-Agent': 'mosslight-tools'})
    try:
        with urllib.request.urlopen(req, timeout=420) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 423: return dict(pending=True)
        sys.exit(f'PixelLab {path}: HTTP {e.code} {e.read()[:300].decode(errors="replace")}')
def to_world_palette(im):
    """Nearest world-palette index per pixel, so day, night and season tables grade the art like everything else."""
    from pixelart.palette import PAL
    pal = np.array(PAL.day[1:], dtype=np.int32); a = np.array(im.convert('RGBA'), dtype=np.int32); d = ((a[:, :, None, :3] - pal[None, None]) ** 2).sum(3); out = (d.argmin(2) + 1).astype(np.uint8); out[a[:, :, 3] < 128] = 0; return out
def image(a):
    r = call('/create-image-pixflux', dict(description=a.prompt, image_size=dict(width=a.size, height=a.size), no_background=not a.background, view=a.view, **({'seed': a.seed} if a.seed is not None else {})))
    raw = Image.open(io.BytesIO(base64.b64decode(r['image']['base64'].split(',')[-1]))); os.makedirs(OUT, exist_ok=True); raw.save(os.path.join(OUT, a.name + '_raw.png')); Image.fromarray(to_world_palette(raw), 'L').save(os.path.join(OUT, a.name + '_idx.png'))
    man = os.path.join(OUT, 'provenance.json'); m = json.load(open(man)) if os.path.exists(man) else {}; m[a.name] = dict(source='PixelLab', endpoint='create-image-pixflux', prompt=a.prompt, size=a.size, seed=a.seed, usage=r.get('usage')); json.dump(m, open(man, 'w'), indent=1); print('wrote', a.name, r.get('usage'))
if __name__ == '__main__':
    p = argparse.ArgumentParser(); s = p.add_subparsers(dest='cmd', required=True); s.add_parser('balance'); i = s.add_parser('image'); i.add_argument('prompt'); i.add_argument('--size', type=int, default=48); i.add_argument('--name', required=True); i.add_argument('--view', default='high top-down'); i.add_argument('--seed', type=int); i.add_argument('--background', action='store_true')
    a = p.parse_args(); print(json.dumps(call('/balance'))) if a.cmd == 'balance' else image(a)
