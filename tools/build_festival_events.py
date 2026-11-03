"""Writes the four festival scene definitions (assets/events/fest_*.json): props placed by hand around one focal point each."""
import json, math, os, sys, random
sys.path.insert(0, os.path.dirname(__file__))
from pixelart.objects import build_library, build_library_extended
from pixelart.scene_clearing import build
_sc = build(build_library_extended(build_library()))
TREES = [(p.sprite.name, p.x, p.y) for p in _sc.placements if p.layer == 'ysort' and p.sprite.name.split('_')[0] in ('rowan',)]
OAKS = [(p.x, p.y) for p in _sc.placements if p.layer == 'ysort' and p.sprite.name.startswith(('oak', 'birch')) and 150 < p.x < 720 and 120 < p.y < 420]
E = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets/events/')
def L(x, y, r=22, col=(1, .82, .55), i=.85, kind='lantern'): return dict(x=x, y=y, radius=r, color=list(col), intensity=i, kind=kind)
ring = [.2 + i * .72 for i in range(8)]; wring = [3.0, 3.5, 4.0, 4.6, 5.2, 5.8, .5, 1.1, 1.7, 2.3]
spring = dict(name='fest_awakening', label='The Awakening (spring festival)', season='spring', hour=17.5, weather='clear', intensity=0, festival=True, grade=dict(key=[255, 236, 222], t=.05, val=1.03, sat=1.04),
  focal='the lone rowan in blossom, lanterns leading to it under the arch',
  props=[dict(sprite='blossom_crown' if n.startswith('rowan') else 'blossom_small', x=x, y=y + 1) for (n, x, y) in TREES] + [dict(sprite=f'petals_{(x + y) % 3}', x=x + random.Random(x).randint(-6, 6), y=y + 6, layer='ground') for (n, x, y) in TREES] + [dict(sprite='blossom_crown', x=418, y=187), dict(sprite='flower_arch', x=452, y=300), dict(sprite='paper_lantern_line', x=430, y=246),
         dict(sprite='wish_post', x=394, y=212), dict(sprite='wish_post', x=444, y=208), dict(sprite='wish_post', x=420, y=222),
         dict(sprite='petals_0', x=418, y=206, layer='ground'), dict(sprite='petals_1', x=470, y=290, layer='ground'), dict(sprite='petals_2', x=390, y=318, layer='ground'), dict(sprite='petals_0', x=440, y=318, layer='ground')] + [dict(sprite=f'flower_drift_{k % 3}', x=x, y=y, layer='ground') for k, (x, y) in enumerate(((372, 196), (452, 196), (392, 232), (446, 236), (350, 216), (480, 214), (520, 300), (396, 330), (344, 350), (432, 356), (300, 170), (494, 160)))] + [dict(sprite='paper_lantern_line', x=x, y=y) for (x, y) in ((360, 270), (500, 240))],
  extra_lights=[L(x, 232, 16, (1, .9, .8), .7, 'string') for x in (408, 420, 432, 444, 455)] + [L(x, 256, 14, (1, .9, .8), .6, 'string') for x in (338, 350, 362, 374, 386)] + [L(x, 226, 14, (1, .9, .8), .6, 'string') for x in (478, 490, 502, 514, 526)] + [L(418, 196, 30, (1, .92, .85), .5, 'glow')])
summer = dict(name='fest_fireflies', label='The Firefly Evening (summer festival)', season='summer', hour=21.5, weather='clear', intensity=0, festival=True, fireflies=3.0, grade=dict(key=[150, 180, 255], t=.06, val=1.0, sat=1.05),
  focal='the pond: a ring of lily lanterns on the water, fireflies over it',
  props=[dict(sprite=f'lily_lantern_{k % 2}', x=int(632 + math.cos(a) * 44), y=int(262 + math.sin(a) * 24)) for k, a in enumerate(ring)] + [dict(sprite='reed_lantern', x=x, y=y) for (x, y) in ((560, 232), (548, 250), (566, 330), (700, 322))] + [dict(sprite='firefly_jar', x=530, y=272), dict(sprite='firefly_jar', x=596, y=272)],
  extra_lights=[L(int(632 + math.cos(a) * 44), int(262 + math.sin(a) * 24) - 8, 28, (1, .8, .48), .95) for a in ring] + [L(x, y - 20, 14) for (x, y) in ((560, 232), (548, 250), (566, 330), (700, 322))])
autumn = dict(name='fest_forgotten', label='The Harvest of Forgotten Things (autumn festival)', season='autumn', hour=18.8, weather='clear', intensity=0, festival=True, grade=dict(key=[255, 180, 110], t=.08, val=1.0, sat=1.08),
  focal='a bonfire and the table of forgotten things on the path to the ruin',
  props=[dict(sprite='bonfire', x=520, y=196), dict(sprite='forgotten_table', x=560, y=176), dict(sprite='leaf_garland', x=500, y=160)] + [dict(sprite='gourd_lantern', x=x, y=y) for (x, y) in ((470, 210), (486, 186), (536, 226), (452, 236))] +
        [dict(sprite='leaf_heap', x=x, y=y) for (x, y) in ((372, 350), (196, 312), (640, 348), (330, 170))] + [dict(sprite='mushroom_ring', x=476, y=338, layer='ground')] + [dict(sprite=f'leaf_carpet_{k % 3}', x=x + 6, y=y + 6, layer='ground') for k, (x, y) in enumerate(OAKS[:10])] + [dict(sprite=f'leaf_carpet_{k % 3}', x=x, y=y, layer='ground') for k, (x, y) in enumerate(((506, 214), (540, 206), (478, 226), (566, 196)))],
  extra_lights=[L(520, 180, 64, (1, .7, .4), 1.0, 'fire')] + [L(x, y - 6, 16, (1, .7, .4), .8) for (x, y) in ((470, 210), (486, 186), (536, 226), (452, 236))] + [L(x, 154, 14, (1, .75, .45), .6, 'string') for x in (480, 500, 520)])
winter = dict(name='fest_silent_tide', label='The Silent Tide (winter festival)', season='winter', hour=22.0, weather='clear', intensity=0, festival=True, grade=dict(key=[170, 200, 255], t=.05, val=1.02, sat=1.0),
  focal='the ice hole in a ring of light, ice lanterns around the frozen pond',
  props=[dict(sprite='tide_ring', x=612, y=290, layer='ground')] + [dict(sprite='ice_lantern', x=int(632 + math.cos(a) * 76), y=int(266 + math.sin(a) * 44)) for a in wring] + [dict(sprite='ice_lantern', x=x, y=y) for (x, y) in ((598, 284), (626, 284))],
  extra_lights=[L(int(632 + math.cos(a) * 76), int(266 + math.sin(a) * 44) - 6, 20, (1, .85, .6), .75) for a in wring] + [L(612, 280, 40, (.7, .9, 1.0), .7, 'glow')])
for ev in (spring, summer, autumn, winter): json.dump(ev, open(E + ev['name'] + '.json', 'w'), indent=0)
print('4 festival scenes'); os.makedirs(os.path.join(os.path.dirname(E.rstrip('/')), 'festivals'), exist_ok=True)

# ---------------------------------------------------------------- festival rules: when, where, what you can do, what you can find
F = {
 'fest_awakening': dict(scene='fest_awakening', season='spring', day=14, **{'from': 8}, to=21, clue_days=3, focus=[418, 200], fx='petals', color='#c88aa8', title='The Awakening',
   hint='Something blooms early in spring. The lone rowan seems to know.', clue='The rowan is covered in tight white buds. In a few days, something will open.',
   blurb='The lone rowan blossoms all at once, and the whole clearing follows. Lanterns lead to it under a woven arch. Wishes are hung on its posts.',
   music=dict(voice='flute', root=523.25, scale=[0, 2, 4, 7, 9, 12, 14]), collectibles=['dawnbell', 'pressed_blossom', 'blossom_dace'],
   spots=[dict(id='dawnbell_a', kind='pick', x=404, y=214, r=16, label='Pick a dawnbell', item='dawnbell', text='A dawnbell: it rings once when picked, then never again.'),
          dict(id='dawnbell_b', kind='pick', x=436, y=216, r=16, label='Pick a dawnbell', item='dawnbell'), dict(id='dawnbell_c', kind='pick', x=372, y=232, r=16, label='Pick a dawnbell', item='dawnbell'),
          dict(id='wish', kind='wish', x=420, y=228, r=18, label='Hang a wish on the rowan', item='pressed_blossom', once='year', text='You tie a strip of cloth to the post and a blossom falls into your hand. You press it in your book.')],
   blockers=[[422, 296, 426, 302], [478, 296, 482, 302], [392, 238, 397, 247], [464, 238, 469, 247]]),
 'fest_fireflies': dict(scene='fest_fireflies', season='summer', day=21, **{'from': 19}, to=26, clue_days=3, focus=[630, 262], fx='fireflies', color='#c8d870', title='The Firefly Evening',
   hint='On one summer night, the pond lights up. More fireflies every evening before it.', clue='There are more fireflies over the pond tonight than any night so far. They seem to be gathering for something.',
   blurb='Lanterns float on lily pads in a ring on the pond, and hundreds of fireflies come down to meet their reflections.',
   music=dict(voice='pad', root=220.0, scale=[0, 3, 5, 7, 10]), collectibles=['firefly_jar', 'moon_lily', 'glowfin'],
   spots=[dict(id='jar', kind='pick', x=532, y=280, r=18, label='Catch fireflies in a jar', item='firefly_jar', limit=3, text='You cup your hands over the light and it settles into the jar.'),
          dict(id='lily', kind='pick', x=604, y=320, r=16, label='Lift a moon lily from the water', item='moon_lily', text='A moon lily, open only tonight. It smells like rain on warm stone.'),
          dict(id='float', kind='float', x=590, y=282, r=18, label='Set a lantern on the water', limit=5, text='Your lantern drifts out to join the ring.')],
   reflect=[[int(632 + __import__('math').cos(a) * 44), int(262 + __import__('math').sin(a) * 24) + 2] for a in ring], blockers=[]),
 'fest_forgotten': dict(scene='fest_forgotten', season='autumn', day=20, **{'from': 15}, to=24, clue_days=2, focus=[520, 196], fx='leaves', color='#c8742a', title='The Harvest of Forgotten Things',
   hint='In autumn the forest gives back what it took. Watch the leaf piles.', clue='The leaves are piling up in odd heaps on the ruin path, as if something is being buried, or uncovered.',
   blurb='The year turns over its leaves. A bonfire burns on the ruin path; lost things surface in the heaps and are laid out on a long table.',
   music=dict(voice='kalimba', root=196.0, scale=[0, 3, 5, 7, 10, 12]), collectibles=['old_compass', 'unsent_letter', 'tin_bird', 'ember_cap'],
   spots=[dict(id='heap_a', kind='search', x=372, y=350, r=18, label='Search the leaf heap', item='old_compass', once='ever', text='Under the leaves: a brass compass. It points at the ruin, not north.'),
          dict(id='heap_b', kind='search', x=196, y=312, r=18, label='Search the leaf heap', item='unsent_letter', once='ever', text='A folded letter, never sent. The ink has run, but one line is still clear.'),
          dict(id='heap_c', kind='search', x=640, y=348, r=18, label='Search the leaf heap', item='tin_bird', once='ever', text='A wind-up tin bird. It still has one chirp in it.'),
          dict(id='heap_d', kind='search', x=330, y=170, r=18, label='Search the leaf heap', text='Only leaves, and a beetle who is annoyed with you.'),
          dict(id='ring', kind='pick', x=476, y=338, r=20, label='Pick an ember cap from the ring', item='ember_cap', limit=2, text='An ember cap: warm to hold, glowing faintly orange underneath.'),
          dict(id='table', kind='offer', x=560, y=184, r=20, label='Leave something on the table', limit=3, text='You leave a {item} on the table among the forgotten things.')],
   blockers=[[509, 188, 531, 198], [538, 168, 582, 178]]),
 'fest_silent_tide': dict(scene='fest_silent_tide', season='winter', day=25, **{'from': 20}, to=28, clue_days=3, focus=[612, 284], fx='snowglow', color='#8aa2c8', title='The Silent Tide',
   hint='Deep in winter, the pond ice turns clear for one night. Listen to the ice before it.', clue='The pond ice rings faintly under your boots, and for a moment you think you see a light far below it.',
   blurb='For one night the pond ice clears like glass. Under it are the lights of the drowned town, still burning. Kneel at the ice hole and fish the deep.',
   music=dict(voice='bells', root=392.0, scale=[0, 2, 7, 9, 12, 14, 19]), collectibles=['drowned_bell', 'frost_glass', 'tide_lantern', 'hush_eel'],
   under_ice=[[600 + (k * 37) % 80 - 10, 236 + (k * 23) % 60, k] for k in range(14)],
   spots=[dict(id='kneel', kind='kneel', x=612, y=292, r=20, label='Kneel at the ice hole', habitat='tide', limit=99),
          dict(id='lantern', kind='pick', x=598, y=290, r=14, label='Light an ice lantern', item='frost_glass', once='year', text='You light the lantern. The ice around it rings like a glass touched with a wet finger.')],
   blockers=[]),
}
json.dump(dict(version=1, festivals=F), open(os.path.join(os.path.dirname(E.rstrip('/')), 'festivals', 'festivals.json'), 'w'), indent=0)
print('festival rules written')
