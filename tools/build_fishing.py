"""Fishing data + vistas. Species records come from fish_data; mechanics read only this JSON."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image
from pixelart.palette import PAL
from pixelart import vistas as V
import fish_data as FD
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(ROOT, 'assets/fishing'); os.makedirs(OUT, exist_ok=True)
HABITATS = {
 'pond': dict(name='Woodland pond', world=True, description='Still, lily-edged water beside the camp. The platform reaches the deep heart of it.', night_risk=0),
 'stream': dict(name='Forest stream', travel_hours=1, travel_energy=2, deep=False, grade='season', night_risk=.15, description='Bright, broken water over stones through the birches. Everything here holds against the current.', anim=dict(flow=[26, 4], glint='water', glints=70, foam=True), float_y=[160, 250]),
 'marsh': dict(name='Peat marsh', travel_hours=2, travel_energy=6, deep=False, grade='season', night_risk=.5, description='Tea-black water under cattails and drowned snags. Most of what lives here can breathe air.', anim=dict(flow=[1, 0], glint='moss', glints=18, foam=False, mist=True), float_y=[180, 250]),
 'lake': dict(name='Alpine lake', travel_hours=4, travel_energy=12, deep=True, grade='season', night_risk=.2, description='A cold turquoise bowl beneath snow peaks. The shelf drops away very suddenly.', anim=dict(flow=[3, 0], glint='ice', glints=60, foam=False), float_y=[150, 255]),
 'tide': dict(name='Beneath the Silent Tide', hidden=True, travel_hours=0, travel_energy=0, deep=True, grade='night', requires={'festival': 'fest_silent_tide', 'text': 'The ice is ordinary ice tonight.'}, night_risk=0, description='The ice is clear as glass. Below it, the drowned town keeps its lights on.', anim=dict(flow=[0, 0], glint='moonlight', glints=10, foam=False, drips=False), float_y=[214, 228], float_dx=14),
 'reservoir': dict(name='Sunken reservoir', travel_hours=3, travel_energy=10, deep=True, grade='night', requires={'found': 'key_old', 'text': 'An old iron door, locked. Somewhere there is a key.'}, night_risk=.6, description='A flooded brick vault below the ruin. It has never heard of the seasons.', anim=dict(flow=[0, 0], glint='moonlight', glints=14, foam=False, drips=True), float_y=[175, 255]),
}
BEHAVIORS = {   # how a hooked fish moves: the fight code reads only these numbers
 'calm':      dict(label='calm', every=[6, 9], len=[.8, 1.2], force=.55, tell=1.0, drift=.03, gain=.8, limit=1.0, slip=4.5, nibbles=1, window=1.6),
 'quick':     dict(label='quick', every=[2.4, 3.6], len=[.5, .9], force=1.0, tell=.6, drift=.05, gain=1.0, limit=1.0, slip=3.4, nibbles=1, window=1.1),
 'erratic':   dict(label='erratic', every=[1.8, 3.2], len=[.35, .8], force=.85, tell=.5, drift=.07, gain=1.05, limit=1.0, slip=3.2, nibbles=2, window=1.1, jink=True),
 'strong':    dict(label='strong', every=[4, 6], len=[1.6, 2.4], force=1.5, tell=.95, drift=.07, gain=1.2, limit=1.0, slip=4, nibbles=2, window=1.4),
 'deep':      dict(label='deep-diving', every=[5, 7], len=[2.2, 3.2], force=1.05, tell=.9, drift=.08, gain=1.05, limit=1.0, slip=4, nibbles=1, window=1.3, dive=True),
 'cautious':  dict(label='cautious', every=[6, 9], len=[.7, 1.1], force=.8, tell=.9, drift=.04, gain=.95, limit=.68, slip=2.6, nibbles=3, window=1.2),
 'surface':   dict(label='surface-feeding', every=[3.6, 5.4], len=[.7, .9], force=.7, tell=.8, drift=.05, gain=1.0, limit=1.0, slip=3.5, nibbles=1, window=1.3, leap=True),
 'nocturnal': dict(label='nocturnal', every=[3.5, 5.5], len=[1, 1.6], force=1.0, tell=.85, drift=.05, gain=1.0, limit=1.0, slip=3.8, nibbles=2, window=1.5, dim=True),
}
TACKLE = {
 'rods': [dict(id='rod', tool=True, name='Primitive rod', tier=0, control=1.0, reach=0), dict(id='rod_wooden', name='Basic wooden rod', tier=1, control=1.15, reach=4), dict(id='rod_improved', name='Improved rod', tier=2, control=1.35, reach=8), dict(id='rod_reinforced', name='Reinforced rod', tier=3, control=1.6, reach=10), dict(id='rod_specialist', name='Specialist rod', tier=4, control=1.9, reach=14)],
 'lines': [dict(id=None, name='Plain cord', strength=1.0), dict(id='line_braided', name='Braided line', strength=1.25), dict(id='line_wire', name='Wire trace', strength=1.6)],
 'hooks': [dict(id=None, name='Bone hook', grip=1.0), dict(id='hook_iron', name='Iron hook', grip=1.35), dict(id='hook_barbed', name='Barbed hook', grip=1.7)],
 'floats': [dict(id=None, name='Cork float', sense=0), dict(id='float_quill', name='Quill float', sense=.45)],
 'baits': [dict(id=None, kind=None, name='Bare hook'), dict(id='worm', kind='worm', name='Worms'), dict(id='insect_bait', kind='insect', name='Insects'), dict(id='baitfish', kind='baitfish', name='Baitfish'), dict(id='dough_bait', kind='dough', name='Plant dough'), dict(id='night_bait', kind='night', name='Night bait'),
           dict(id='lure_spinner', kind='lure_spinner', lure=True, name='Spinner lure', better_in=['rain', 'stream', 'lake']), dict(id='lure_fly', kind='lure_fly', lure=True, name='Tied fly', better_in=['clear', 'stream']), dict(id='lure_moth', kind='lure_moth', lure=True, name='Moth lure'), dict(id='lure_glow', kind='lure_glow', lure=True, name='Glow lure', better_in=['fog', 'reservoir'])],
}
RARITY = dict(common=dict(weight=30, tier=0, wait=1), uncommon=dict(weight=12, tier=0, wait=1.25), rare=dict(weight=4.5, tier=1, wait=1.5), very_rare=dict(weight=2.2, tier=2, wait=1.7), exceptional=dict(weight=1.4, tier=3, wait=1.8), legendary=dict(weight=1, tier=3, wait=2))
for h, mk in V.ALL.items(): Image.fromarray(mk().a, 'L').save(os.path.join(OUT, f'vista_{h}_idx.png'))
c, ox, oy = V.trail_sign(); Image.fromarray(c.a, 'L').save(os.path.join(OUT, 'trail_sign_idx.png'))
json.dump(dict(version=1, fish=FD.RECORDS, habitats=HABITATS, behaviors=BEHAVIORS, tackle=TACKLE, rarity=RARITY, pond=dict(x=630, y=268, r=78), sign=dict(x=454, y=338, ox=ox, oy=oy, w=c.w, h=c.h), vista=dict(w=V.W, h=V.H, stand=[400, 318])), open(os.path.join(OUT, 'fishing.json'), 'w'), indent=0)
lut = PAL.day
for h, mk in V.ALL.items(): mk().save(os.path.join(ROOT, f'renders/vista_{h}.png'), lut=lut)
print(len(FD.RECORDS), 'species', len(HABITATS), 'habitats')
