"""Reads the three narrative source files (docs/narrative/*.md, copies of CHARACTER_BIBLE, DIALOGUE_LIBRARY and
WORLD_NARRATIVE) and turns them into data the game can use. The writing itself is never retyped or rewritten here:
every spoken line comes straight out of the markdown, changing only typography the game font cannot draw
(curly quotes become straight ones).

    python3 tools/narrative.py          writes assets/social/narrative.json and prints a coverage summary
"""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'docs', 'narrative')
# library name -> the engine id that already exists in saves (the sprite, schedule and memory systems key on it)
CHAR_IDS = {'Nera': 'ebb', 'Pip': 'pip', 'Sella': 'wick', 'Orun': 'burl', 'Morrow': 'tessel', 'Luma': 'lull'}
ID_OF_BIBLE = {'Keeper of the Pond — Nera': 'Nera', 'Little Forager — Pip': 'Pip', 'Lantern Keeper — Sella': 'Sella', 'Rootbound Elder — Orun': 'Orun',
               'Mechanical Wanderer — M-4, usually “Morrow”': 'Morrow', 'Mechanical Wanderer — Morrow': 'Morrow', 'Dreaming Creature — Luma': 'Luma'}

def clean(t):
    """typography only: the game font has no curly quotes"""
    return t.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'").strip()

def read(name): return open(os.path.join(SRC, name), encoding='utf-8').read()

# ---------------------------------------------------------------- DIALOGUE_LIBRARY.md
TURN = re.compile(r'\*\*([A-Za-z][A-Za-z\- ]*?):\*\*\s*“(.*?)”(?=\s*\*\*|\s*$)')
def parse_turns(s, names):
    out = []
    for who, text in TURN.findall(s):
        out.append(dict(who='player' if who == 'Player' else 'npc', speaker=who, text=clean(text)))
    return out

def parse_library():
    txt = read('DIALOGUE_LIBRARY.md'); chars = {}; cross = []; choices = {}; cur = None; group = None; mode = None
    for line in txt.splitlines():
        if line.startswith('## '):
            h = line[3:].strip(); mode = None
            if ' — ' in h and h.split(' — ')[-1] in CHAR_IDS: cur = h.split(' — ')[-1]; chars[cur] = dict(name=cur, title=h.split(' — ')[0], group_order=[], exchanges=[])
            elif h.startswith('Cross-character'): cur = None; mode = 'cross'
            elif h.startswith('Choice responses'): cur = None; mode = 'choice'
            else: cur = None
        elif line.startswith('### ') and cur: group = line[4:].strip()
        elif mode == 'choice' and line.startswith('- **'):
            m = re.match(r'- \*\*([A-Za-z]+):\*\*\s*“(.*)”\s*$', line)
            if m: choices[m.group(1)] = clean(m.group(2))
        else:
            m = re.match(r'(\d+)\.\s+\*\*(.+?)\*\*\s+—\s+(.*)$', line)
            if not m: continue
            n, tag, rest = int(m.group(1)), m.group(2), m.group(3)
            turns = parse_turns(rest, None)
            if not turns: raise SystemExit(f'no turns parsed: {line[:80]}')
            if mode == 'cross':
                cross.append(dict(n=n, title=tag, turns=turns))
            elif cur:
                chars[cur]['exchanges'].append(dict(id=f'{CHAR_IDS[cur]}.{n}', n=n, group=group, tag=tag, first=turns[0]['who'], turns=[dict(who=t['who'], text=t['text']) for t in turns]))
    return chars, cross, choices

# ---------------------------------------------------------------- CHARACTER_BIBLE.md
def parse_bible():
    txt = read('CHARACTER_BIBLE.md'); chars = {}; cur = None; shared = ''; cast_table = []
    parts = re.split(r'^## ', txt, flags=re.M)
    for part in parts[1:]:
        head, _, body = part.partition('\n'); head = head.strip()
        if head.startswith('Shared continuity'): shared = body.strip(); continue
        if head.startswith('Voice separation'): cast_table = [l for l in body.splitlines() if l.startswith('|')]; continue
        name = head.split('—')[-1].strip().split(',')[0].strip(); name = 'Morrow' if name.startswith('M-4') else name
        d = dict(name=name, title=head.split('—')[0].strip(), sections={})
        for m in re.finditer(r'\*\*(.+?):\*\*\s*(.*?)(?=\n\n\*\*|\Z)', body, flags=re.S):
            d['sections'][m.group(1).strip()] = clean(m.group(2).strip())
        chars[name] = d
    return chars, clean(shared), cast_table

# ---------------------------------------------------------------- WORLD_NARRATIVE.md
def parse_world():
    txt = read('WORLD_NARRATIVE.md'); out = dict(intro=[], history=[], living=[], folklore=[], places=[], creatures=[], seasons=[], threads=[], boundaries=[])
    sec = None; sub = None
    for block in re.split(r'\n(?=## |### )', txt):
        head = block.splitlines()[0]; body = '\n'.join(block.splitlines()[1:]).strip()
        if head.startswith('## The shape'): sec = 'intro'; out['intro'] = [clean(p) for p in body.split('\n\n') if p.strip()]
        elif head.startswith('## What happened'): sec = 'history'; out['history'] = [clean(p) for p in body.split('\n\n') if p.strip()]
        elif head.startswith('## The living change'): sec = 'living'; out['living'] = [clean(p) for p in body.split('\n\n') if p.strip()]
        elif head.startswith('## Folklore'): sec = 'folklore'; out['folklore_note'] = clean(body)
        elif head.startswith('## Places'): sec = 'places'
        elif head.startswith('## Creatures'): sec = 'creatures'; out['creature_items'] = [clean(l[2:]) for l in body.splitlines() if l.startswith('- ')]; out['creature_note'] = clean([l for l in body.splitlines() if l and not l.startswith('-')][-1])
        elif head.startswith('## Seasonal story'): sec = 'seasons'; out['seasons'] = [clean(l) for l in body.splitlines() if l.startswith('**')]
        elif head.startswith('## Shared narrative'): sec = 'threads'; out['threads'] = [clean(p) for p in body.split('\n\n') if p.strip()]
        elif head.startswith('## Social boundaries'): sec = 'boundaries'; out['boundaries'] = [clean(p) for p in body.split('\n\n') if p.strip()]
        elif head.startswith('### ') and sec in ('folklore', 'places'):
            title = head[4:].strip(); key, _, name = title.partition(': ') if sec == 'folklore' else ('', '', title)
            out[sec].append(dict(title=name if sec == 'folklore' else title, place_type=key, paragraphs=[clean(p) for p in body.split('\n\n') if p.strip()]))
    return out

def build():
    lib, cross, choices = parse_library(); bible, shared, table = parse_bible(); world = parse_world()
    for n in lib: assert n in bible, ('bible missing', n)
    data = dict(ids=CHAR_IDS, characters={n: dict(id=CHAR_IDS[n], name=n, title=lib[n]['title'], bible=bible[n]['sections'], exchanges=lib[n]['exchanges']) for n in lib}, cross=cross, choices=choices, shared=shared, voice_table=table, world=world)
    os.makedirs(os.path.join(ROOT, 'assets', 'social'), exist_ok=True)
    json.dump(data, open(os.path.join(ROOT, 'assets', 'social', 'narrative.json'), 'w'), indent=0, ensure_ascii=False)
    return data

if __name__ == '__main__':
    d = build(); tot = 0
    for n, c in d['characters'].items():
        ex = c['exchanges']; tot += len(ex); first = {k: sum(1 for e in ex if e['first'] == k) for k in ('npc', 'player')}
        print(f"{n:7s} {len(ex):2d} exchanges (npc-first {first['npc']}, player-first {first['player']}), bible sections: {len(c['bible'])}")
    print('cross-character:', len(d['cross']), ' choice responses:', len(d['choices']), ' folklore:', len(d['world']['folklore']), ' places:', len(d['world']['places']), ' total exchanges:', tot)
