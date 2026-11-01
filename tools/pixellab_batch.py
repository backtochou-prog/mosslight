"""Run a named batch of PixelLab generations. Every call is logged to provenance.json; a spec already on disk is never paid for twice."""
import sys, os, json, base64, io, time, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image
import numpy as np
from pixelart.palette import PAL
from pixellab import call, OUT
STYLE = 'cozy farming life game art, warm saturated natural colors, soft rounded forms, clean pixel clusters, three-quarter top-down view, lit from upper left'
def swatch(fams):
    """A colour image from our own palette ramps, so generated art starts inside the game's colour language."""
    cols = [PAL.day[PAL.index[(f, r)]] for f in fams for r in range(len(PAL.ramp(f)))]; im = Image.new('RGB', (len(cols), 1)); im.putdata(cols); b = io.BytesIO(); im.save(b, 'PNG')
    return dict(type='base64', base64=base64.b64encode(b.getvalue()).decode())
def save_b64(s, path):
    im = Image.open(io.BytesIO(base64.b64decode(s.split(',')[-1]))).convert('RGBA'); im.save(path); return im
def one(spec):
    os.makedirs(OUT, exist_ok=True); name = spec['name']; path = os.path.join(OUT, name + '.png')
    if os.path.exists(path): return name, 'cached'
    if spec['kind'] == 'image':
        body = dict(description=spec['prompt'] + ', ' + STYLE, image_size=dict(width=spec['w'], height=spec['h']), no_background=spec.get('no_bg', True), view='high top-down', outline=spec.get('outline', 'selective outline'), shading=spec.get('shading', 'detailed shading'), detail=spec.get('detail', 'highly detailed'), seed=spec.get('seed', 11))
        if spec.get('fams'): body['color_image'] = swatch(spec['fams'])
        r = call('/create-image-pixflux', body); save_b64(r['image']['base64'], path); return name, r.get('usage')
    if spec['kind'] == 'tileset':
        r = call('/create-tileset', dict(lower_description=spec['lower'], upper_description=spec['upper'], transition_description=spec.get('trans', ''), tile_size=dict(width=16, height=16), shading='detailed shading', detail='highly detailed', transition_size=spec.get('ts', .25), seed=spec.get('seed', 11)))
        tid = r.get('tileset_id') or r.get('id') or (r.get('data') or {}).get('tileset_id')
        print('tileset', name, tid, flush=True)
        for _ in range(60):
            time.sleep(10); t = call('/tilesets/' + str(tid))
            if not t.get('pending'): break
        json.dump(t, open(os.path.join(OUT, name + '.json'), 'w')); Image.new('L', (1, 1)).save(path); return name, t.get('usage') or r.get('usage')
def run(specs):
    with cf.ThreadPoolExecutor(1) as ex: res = list(ex.map(one, specs))
    man = os.path.join(OUT, 'provenance.json'); m = json.load(open(man)) if os.path.exists(man) else {}
    for s, (n, u) in zip(specs, res):
        if u != 'cached': m[n] = dict(source='PixelLab', spec={k: v for k, v in s.items() if k != 'name'}, usage=u)
    json.dump(m, open(man, 'w'), indent=1); print(res); print(json.dumps(call('/balance')))
if __name__ == '__main__': run(json.load(open(sys.argv[1])))
