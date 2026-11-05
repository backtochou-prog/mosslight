"""The MOSSlight visual pilot pack, generated with PixelLab (create_image_pro / tilesets) on the game's own palette.

Every request is recorded in assets/pixellab/pilot.json (description, size, seed, palette families, job id, cost) and
every candidate is kept as a source file under assets/pixellab/src/<asset>/, so choices can be revisited.

    python3 tools/pixellab/pilot.py submit NAME [NAME...]    # queue jobs
    python3 tools/pixellab/pilot.py fetch NAME [NAME...]     # wait, download candidates, write contact sheets
"""
import json, os, sys, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp import MCP, palette_hex, text_of, download, contact_sheet
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = os.path.join(ROOT, 'assets/pixellab/pilot.json')
STYLE = ("cozy top-down farming-game pixel art in the spirit of a handcrafted 16-bit valley, three-quarter top-down view, "
         "light from the upper left, soft dark selective outline, clean readable clusters, no ground, no cast shadow")
ANCHOR = os.path.join(ROOT, 'assets/pixellab/src/oak/cand_06.png')       # the approved oak: every object borrows its outline, detail and shading

ASSETS = {
    'pine': dict(w=44, h=80, fams=('pine', 'wood'), d="a tall evergreen fir tree with tiers of drooping dark green boughs, straight brown trunk at the base"),
    'rocks': dict(w=48, h=40, fams=('stone', 'moss', 'grass'), d="a natural rock formation: one large grey boulder with a smaller stone leaning on it and pebbles at its foot, flat planes, moss on top, grass tufts at the base"),
    'rocks_small': dict(w=32, h=24, fams=('stone', 'moss', 'grass'), d="a small cluster of two or three grey stones with moss, grass tuft at the base"),
    'mushrooms': dict(w=32, h=32, fams=('shroom', 'shroom_stem', 'wood', 'moss'), d="a small cluster of three forest mushrooms of different sizes, brown and red caps with pale stems, moss at their base"),
    'flowers': dict(w=32, h=32, fams=('flower_w', 'flower_y', 'flower_b', 'flower_p', 'grass'), d="a small clump of wildflowers growing from a tuft of leaves: daisies, buttercups and bluebells"),
    'bush': dict(w=48, h=40, fams=('shrub', 'berry', 'wood'), d="a round leafy shrub built from overlapping leaf clumps, a few red berries tucked in"),
    'log': dict(w=64, h=32, fams=('wood', 'moss', 'shroom', 'grass'), d="a fallen tree log lying horizontally with bark texture, a sawn end showing rings, moss on top, small shelf fungus on its side"),
    'tent': dict(w=80, h=64, fams=('canvas', 'rope', 'wood', 'tent_interior', 'flower_b', 'berry'), d="a canvas ridge camping tent, front view slightly from the right, door flaps rolled and tied back showing a dark interior with a blue bedroll, guy ropes to wooden pegs, a sewn patch"),
    'campfire': dict(w=48, h=48, fams=('stone', 'wood', 'fire', 'ember', 'earth'), d="a campfire: a ring of nine grey stones around an ash bed, split logs leaning into a small tipi, bright flames with a yellow core and glowing embers"),
    'lantern': dict(w=24, h=48, fams=('wood', 'metal', 'lantern_glass', 'stone'), d="a wooden lantern post with a crossarm and an iron lantern with warm glowing glass hanging from it, stones wedged at its foot"),
    'woodpile': dict(w=48, h=40, fams=('wood', 'wood_grey'), d="a neat stack of split firewood rounds seen end-on, pale end grain with rings, held between two wooden stakes"),
    'chopblock': dict(w=32, h=32, fams=('wood', 'metal'), d="a tree stump used as a chopping block with an axe embedded in the top and wood chips around its base"),
    'crate': dict(w=32, h=32, fams=('wood', 'metal', 'rope'), d="a wooden supply crate with a dented metal kettle and a tin mug on top and a coil of rope on its side"),
    'bench': dict(w=48, h=32, fams=('wood', 'moss'), d="a rustic log bench: a split log seat on two short stump legs, worn smooth on top"),
    'fern': dict(w=28, h=24, fams=('fern', 'grass'), d="a forest fern: five or six arching fronds with fine leaflets fanning from one crown, lighter tips"),
    'tuft': dict(w=20, h=16, fams=('grass', 'reed'), d="a small tuft of meadow grass blades, a few lighter tips"),
    'tallgrass': dict(w=24, h=28, fams=('grass', 'reed'), d="a clump of tall wild grass with long arching blades and a couple of seed heads"),
    # 2D pass (the user: keep everything 2D): seen straight from the front and a little above, no corner angle, no perspective
    'tent2d': dict(w=80, h=64, fams=('canvas', 'rope', 'wood', 'tent_interior', 'flower_b', 'berry'), seed=21,
                   d="a canvas A-frame camping tent seen straight from the front, flat 2D front view like a classic 16-bit RPG: a symmetrical triangular front with the door flaps tied back on both sides, dark interior with a blue bedroll, the roof slope visible above, guy ropes to pegs on both sides. Orthographic, not isometric, no corner angle"),
    'crate2d': dict(w=32, h=32, fams=('wood', 'metal', 'rope'), seed=21,
                    d="a wooden supply crate seen straight from the front, flat 2D front view like a classic 16-bit RPG: plank front face with the lid's top edge visible, a small kettle and a tin mug on top. Orthographic, not isometric, no corner angle"),
    'bench2d': dict(w=48, h=24, fams=('wood', 'moss'), seed=21,
                    d="a rustic log bench seen straight from the front, flat 2D front view like a classic 16-bit RPG: a long split-log seat on two short stump legs, the seat's top surface visible, a little moss. Orthographic, not isometric, horizontal, no corner angle"),
    'woodpile2d': dict(w=48, h=40, fams=('wood', 'wood_grey'), seed=21,
                       d="a stack of split firewood seen straight from the front, flat 2D front view like a classic 16-bit RPG: round log ends facing the viewer in neat rows between two upright stakes. Orthographic, not isometric, no corner angle"),
    # second pass at true scale: the 32 px mushrooms and flowers read as big as a bush beside the camper
    'mushrooms_s': dict(w=20, h=20, fams=('shroom', 'shroom_stem', 'wood', 'moss'), d="a tiny cluster of two or three small forest mushrooms with brown and red caps and pale stems on a little moss"),
    'flowers_s': dict(w=20, h=20, fams=('flower_w', 'flower_y', 'flower_b', 'flower_p', 'grass'), d="a tiny clump of wildflowers on a small tuft of leaves, a few small blossoms"),
}


def db():
    return json.load(open(DB)) if os.path.exists(DB) else {}


def submit(names):
    m = MCP(); d = db()
    anchor = base64.b64encode(open(ANCHOR, 'rb').read()).decode() if os.path.exists(ANCHOR) else None
    for n in names:
        a = ASSETS[n]
        args = {'description': a['d'] + '. ' + STYLE, 'width': a['w'], 'height': a['h'], 'no_background': True,
                'palette': palette_hex(*a['fams']), 'palette_name': 'MOSSlight', 'seed': a.get('seed', 11)}
        if anchor and n != 'oak': args['style_image_base64'] = anchor; args['style_copy'] = ['outline', 'detail', 'shading']
        r = text_of(m.call('create_image_pro', args))
        job = [l.split(': ', 1)[1] for l in r.splitlines() if l.startswith('job_id:')][0]
        cands = int([l.split(': ', 1)[1] for l in r.splitlines() if l.startswith('candidates:')][0])
        cost = [l.split(': ', 1)[1] for l in r.splitlines() if l.startswith('cost:')]
        d[n] = dict(tool='create_image_pro', description=args['description'], size=[a['w'], a['h']], seed=args['seed'], palette_families=list(a['fams']),
                    style_anchor='src/oak/cand_06.png' if 'style_image_base64' in args else None, job_id=job, candidates=cands, cost=cost[0] if cost else None)
        print(n, job, cands, cost)
    json.dump(d, open(DB, 'w'), indent=1)


def fetch(names):
    m = MCP(); print(text_of(m.call('wait_for_jobs', {'timeout_seconds': 540}))[:300]); d = db()
    for n in names:
        e = d[n]; ps = download(e['job_id'], os.path.join(ROOT, 'assets/pixellab/src', n), e['candidates'])
        contact_sheet(ps, f'/tmp/sheet_{n}.png', z=3 if max(e['size']) > 40 else 5); print(n, len(ps))


if __name__ == '__main__':
    {'submit': submit, 'fetch': fetch}[sys.argv[1]](sys.argv[2:])


GRASS_BASE = 'a056a28f-6107-4c23-9cee-4011af94f303'          # the approved grass (upper base tile of ts_grass_dirt2)
CALM = "mostly flat calm colour with only a few sparse soft texture marks, large quiet areas, no speckles, no noise, low contrast"
TILESETS = {
    'ts_grass_forest3': dict(lower="shaded forest floor: dark moss and a little leaf litter, " + CALM, upper="soft meadow grass", upper_base='264a9b50-d544-4a09-8f08-0d02e3615970',
                             fams=('forest', 'leaf_litter', 'grass', 'moss'), transition=0.0, raggedness=0.45, amp=0.15, shading='basic shading', detail='low detail'),
    'ts_water_grass3': dict(lower="calm clear pond water, deep blue, " + CALM, upper="soft meadow grass", upper_base='264a9b50-d544-4a09-8f08-0d02e3615970',
                            fams=('water', 'grass', 'mud', 'sand'), transition=0.25, raggedness=0.3, amp=0.12, tdesc="a low earthy bank", shading='basic shading', detail='low detail'),
    'ts_grass_clover3': dict(lower="slightly deeper green meadow grass with a few clover leaves, " + CALM, upper="soft meadow grass", upper_base='264a9b50-d544-4a09-8f08-0d02e3615970',
                             fams=('grass', 'fern'), transition=0.0, raggedness=0.6, amp=0.2, shading='basic shading', detail='low detail'),
    'ts_grass_dirt3': dict(lower="smooth trodden dirt path in warm brown, " + CALM, upper="soft meadow grass in one calm green, " + CALM,
                           fams=('dirt', 'grass', 'earth'), transition=0.0, raggedness=0.35, amp=0.15, shading='basic shading', detail='low detail'),
    'ts_grass_clover': dict(lower="deeper, slightly darker meadow grass with clover leaves and longer blades, calm low contrast", upper="soft lush grass", upper_base=GRASS_BASE,
                            fams=('grass', 'fern'), transition=0.0, raggedness=0.6, amp=0.2),
    'ts_grass_forest2': dict(lower="shaded forest floor: dark moss, fallen needles and leaf litter, calm low contrast", upper="soft lush grass", upper_base=GRASS_BASE,
                             fams=('forest', 'leaf_litter', 'grass', 'moss'), transition=0.0, raggedness=0.5, amp=0.15),
    'ts_water_grass2': dict(lower="calm clear pond water, deep blue with a few soft glints", upper="soft lush grass", upper_base=GRASS_BASE,
                            fams=('water', 'grass', 'mud', 'sand'), transition=0.25, raggedness=0.35, amp=0.12, tdesc="a low earthy bank with wet mud at the waterline"),
    'ts_grass_dirt2': dict(lower="smooth trodden dirt path in warm brown, gently mottled, a few small pebbles, low contrast", upper="soft lush grass in calm close green tones, fine short blade texture, low contrast, no bright speckles",
                           fams=('dirt', 'grass', 'earth'), transition=0.0, raggedness=0.4, amp=0.15),
    'ts_grass_dirt': dict(lower="soft brown dirt path, trodden earth with small pebbles and fine grit", upper="lush meadow grass with small blade clumps in close green tones",
                          fams=('dirt', 'grass', 'earth'), transition=0.0, raggedness=0.45, amp=0.12),
    'ts_grass_forest': dict(lower="shaded forest floor: dark moss, fallen needles and leaf litter", upper="lush meadow grass with small blade clumps in close green tones",
                            fams=('forest', 'leaf_litter', 'grass', 'moss'), transition=0.0, raggedness=0.5, amp=0.15),
    'ts_water_grass': dict(lower="calm clear pond water, deep blue with a few soft glints", upper="lush meadow grass with small blade clumps",
                           fams=('water', 'grass', 'mud', 'sand'), transition=0.25, raggedness=0.35, amp=0.12, tdesc="a low earthy bank with wet mud at the waterline"),
}


def submit_tilesets(names):
    m = MCP(); d = db()
    for n in names:
        t = TILESETS[n]
        args = dict(lower_description=t['lower'], upper_description=t['upper'], mode='pro', tile_size=16, transition_size=t['transition'],
                    raggedness=t['raggedness'], boundary_amplitude=t['amp'], boundary_seed=3, view='high top-down', shading=t.get('shading', 'detailed shading'), detail=t.get('detail', 'highly detailed'),
                    palette=palette_hex(*t['fams']), palette_name='MOSSlight')
        if t.get('tdesc'): args['transition_description'] = t['tdesc']
        if t.get('upper_base'): args['upper_base_tile_id'] = t['upper_base']                 # chain onto the approved grass so every set shares it
        r = text_of(m.call('create_topdown_tileset', args))
        tid = [l.split(': ', 1)[1].strip() for l in r.splitlines() if 'tileset_id' in l.lower() or l.lower().startswith('id:')]
        d[n] = dict(tool='create_topdown_tileset', args={k: v for k, v in args.items() if k != 'palette'}, palette_families=list(t['fams']), response=r[:600], tileset_id=tid[0] if tid else None)
        print(n, d[n]['tileset_id']); print(r[:300])
    json.dump(d, open(DB, 'w'), indent=1)


def fetch_tileset(name):
    """Download a finished Wang tileset: the sheet, its metadata (corner layout), the example map; keep everything."""
    import urllib.request, time, re
    m = MCP(); d = db(); tid = d[name]['tileset_id']; out = os.path.join(ROOT, 'assets/pixellab/src', name); os.makedirs(out, exist_ok=True)
    for _ in range(60):
        r = text_of(m.call('get_topdown_tileset', {'tileset_id': tid}))
        if 'completed' in r.lower() or 'download' in r.lower(): break
        time.sleep(15)
    open(os.path.join(out, 'response.txt'), 'w').write(r)
    urls = re.findall(r'https?://\S+', r)
    from mcp import _key
    for u in urls:
        u = u.rstrip(').,')
        fn = os.path.basename(u.split('?')[0]) or 'file'
        try:
            req = urllib.request.Request(u, headers={'Authorization': 'Bearer ' + _key()} if 'pixellab.ai' in u else {})
            with urllib.request.urlopen(req, timeout=120) as resp: data = resp.read()
            open(os.path.join(out, fn), 'wb').write(data); print('saved', fn, len(data))
        except Exception as e: print('skip', u[:80], e)
    return r
