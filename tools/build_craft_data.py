"""Crafting + construction data. One source for balance: edit here, run this file.
Writes assets/build/recipes.json and components.json; CRAFTED_ITEMS is imported by build_items.py."""
import os, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def I(id, name, desc, stack=20, value=2, weight=0.3, sprite=None):
    return dict(id=id, name=name, description=desc, category='crafted', rarity='common', icon=id, stack=stack, value=value, weight=weight, gathering='crafted', tool=None,
                seasons='all', time='any', weather='any', habitat='made by hand', crafting='', collectible='crafted', sprite=sprite)
MATERIALS = [I('plank', 'Plank', 'A split board, still smelling of the tree.', 30), I('cord', 'Cord', 'Plant fibre twisted until it holds.', 30), I('nails', 'Nails', 'Cut from old scrap and hammered straight.', 50, 1, .02),
             I('stone_block', 'Stone block', 'Squared on four faces, near enough.', 20, 3, 1.2), I('iron_ingot', 'Iron ingot', 'Rough, dark and honest.', 10, 12, 1.5), I('glass_pane', 'Glass pane', 'Old glass melted and poured flat. A little wavy.', 10, 6, .4),
             I('hinge', 'Hinge', 'Two leaves and a pin. It makes a door a door.', 10, 5, .2), I('cloth', 'Woven cloth', 'Coarse, warm, and yours.', 20, 4, .1)]
def N(id, name, desc, cat, rarity, value=8, stack=10, use=None):
    d = I(id, name, desc, stack, value, .1); d.update(category=cat, rarity=rarity, gathering='creature' if cat == 'creature' else 'hand', collectible='creature' if cat == 'creature' else 'rare', use=use); return d
NIGHT_ITEMS = [N('luminous_spores', 'Luminous spores', 'Soft pale dust that keeps its glow for days. Shaken loose, never taken by force.', 'rare_find', 'rare', 18),
  N('nightglass', 'Nightglass', 'Black glass that grows on the pond bank after midnight. By day it looks like wet stone.', 'rare_find', 'very_rare', 45, 5),
  N('rot_fiber', 'Rot fibre', 'Pale threads from a Wanderer. Stronger than they look; they still twitch a little.', 'creature', 'common', 4, 20),
  N('stalker_lens', 'Stalker lens', 'A hard clear bead from one of its three eyes. Things look closer through it.', 'creature', 'rare', 22, 10),
  N('burrower_plate', 'Burrower ring', 'A flexible ringed plate from the grub, like horn and leather at once.', 'creature', 'uncommon', 10),
  N('howler_sac', 'Throat sac', 'Empty now. It still hums when the wind crosses it.', 'creature', 'rare', 25, 5),
  N('brute_hide', 'Stoneplate', 'Living rock from a Brute shoulder, moss still growing on it.', 'creature', 'very_rare', 60, 5),
  N('healing_tonic', 'Moondew tonic', 'Mint steeped in moondew. Restores a good deal of health.', 'crafted', 'uncommon', 20, 5, {'heal': 40}),
  N('ghost_salve', 'Ghostcap salve', 'Cold on the skin, then nothing hurts for a while. Restores all health.', 'crafted', 'rare', 70, 3, {'heal': 100})]
def TK(id, name, desc, rarity='common', value=6, stack=20, cat='tackle'):
    d = I(id, name, desc, stack, value, .05); d.update(category=cat, rarity=rarity, gathering='crafted', collectible='tackle'); return d
TACKLE_ITEMS = [TK('rod_wooden', 'Basic wooden rod', 'A straight ash pole with a proper tip ring. Better control than the reed.', 'common', 18, 1), TK('rod_improved', 'Improved rod', 'Jointed, with wire guides. It bends where it should.', 'uncommon', 45, 1), TK('rod_reinforced', 'Reinforced rod', 'Iron-sleeved at the butt. It will not be the first thing to give.', 'rare', 90, 1), TK('rod_specialist', 'Specialist rod', 'Resin-laid strips and a moonstone tip guide. For the fish in the stories.', 'very_rare', 240, 1),
 TK('line_braided', 'Braided line', 'Three cords laid as one. Survives a strong run.', 'common', 12, 1), TK('line_wire', 'Wire trace', 'Fine wire above the hook. Teeth do not bother it.', 'uncommon', 30, 1), TK('hook_iron', 'Iron hook', 'Holds better in a soft mouth.', 'common', 10, 1), TK('hook_barbed', 'Barbed hook', 'Once in, it stays in. A slack line will not lose the fish so easily.', 'uncommon', 26, 1), TK('float_quill', 'Quill float', 'Feather-light. Gives you longer to answer a bite.', 'common', 8, 1),
 TK('worm', 'Worms', 'Fat and unwilling. Almost everything eats them.', 'common', 1, 30, 'bait'), TK('insect_bait', 'Insects', 'A pinch of wings and legs from the reeds.', 'common', 1, 30, 'bait'), TK('baitfish', 'Baitfish', 'A small fish on a big hook, for predators.', 'common', 3, 20, 'bait'), TK('dough_bait', 'Plant dough', 'Seed meal and mushroom, kneaded. Carp cannot resist it.', 'common', 2, 30, 'bait'), TK('night_bait', 'Night bait', 'Worm rolled in moondew. It shines faintly, and strange things come to it.', 'uncommon', 8, 20, 'bait'),
 TK('lure_spinner', 'Spinner lure', 'A flashing blade. Predators and bad weather love it. Not eaten, but a snapped line loses it.', 'uncommon', 25, 3), TK('lure_fly', 'Tied fly', 'Feather and thread. Delicate fish take it on clear days.', 'uncommon', 22, 3), TK('lure_moth', 'Moth lure', 'Wings of dust and a real moth body, for the things that rise at night.', 'rare', 55, 3), TK('lure_glow', 'Glow lure', 'Spores set in nightglass. It is the only thing some fish have ever looked at.', 'very_rare', 120, 2)]
import fish_data as _FD
def FV(id, name, desc, rarity, value, stack=5, cat='festival'):
    d = I(id, name, desc, stack, value, .05); d.update(category=cat, rarity=rarity, gathering='festival', collectible='festival'); return d
FEST_ITEMS = [FV('dawnbell', 'Dawnbell', 'A white bell-flower that opens only on the Awakening. It rings once when it is picked, and never again.', 'rare', 40),
 FV('pressed_blossom', 'Pressed rowan blossom', 'A blossom from the lone rowan, pressed flat between the pages of your book. One for each year you hang a wish.', 'uncommon', 15, 10),
 FV('firefly_jar', 'Jar of fireflies', 'A glass jar of borrowed light from the Firefly Evening. Let them go when you are ready.', 'uncommon', 20),
 FV('moon_lily', 'Moon lily', 'A white lily that opens for one night of summer and smells of rain on warm stone.', 'rare', 45),
 FV('old_compass', 'Brass compass', 'Turned up in the autumn leaves. It points at the ruin, not north. It always has.', 'rare', 60, 1),
 FV('unsent_letter', 'Unsent letter', '"If you find the pond still there, it is because we left it alone." The rest has run in the rain.', 'rare', 30, 1),
 FV('tin_bird', 'Tin bird', 'A wind-up bird from the leaf heaps with exactly one chirp left in it. You have not used it yet.', 'rare', 50, 1),
 FV('ember_cap', 'Ember cap', 'A mushroom from the autumn ring, warm in the hand, glowing faintly orange underneath.', 'uncommon', 25),
 FV('drowned_bell', 'Drowned bell', 'A small brass bell from under the Silent Tide. It does not ring in air. In water, faintly, it does.', 'very_rare', 120, 1),
 FV('frost_glass', 'Frost glass', 'A shard of the ice lantern you lit on the Silent Tide. It has not melted. It is not going to.', 'rare', 40),
 FV('carved_fish', 'Carved wooden fish', "A child's carving, smoothed by forty years of pond water. Someone loved it very much.", 'very_rare', 0, 1, 'keepsake')]
FISH_ITEMS = []
for _f in _FD.RECORDS:
    _d = I(_f['id'], _f['name'], _f['description'], {'common': 20, 'uncommon': 10, 'rare': 5}.get(_f['rarity'], 1), _f['value'], round((_f['kg'][0] + _f['kg'][1]) / 2, 3)); _d.update(category='fish', rarity=_f['rarity'], gathering='fishing', collectible='fish', habitat=_f['habitat'], crafting=', '.join(_f['uses']), plate=True); FISH_ITEMS.append(_d)
# id: name, description, station built to craft it, ingredients, minutes, energy
def R(id, station, ingredients, minutes, energy, qty=1, unlock=None, cat='material', result=None, name=None, desc=''):
    return dict(id=id, name=name, description=desc, station=station, ingredients=ingredients, minutes=minutes, energy=energy, result=result or id, qty=qty, unlock=unlock or {'type': 'start'}, category=cat, icon=result or id)
RECIPES = [
 R('cord', 'hand', {'fiber': 2}, 4, 0, 1), R('plank', 'workbench', {'log': 1}, 10, 2, 4, {'type': 'item', 'id': 'log'}), R('plank_fine', 'wood_station', {'log': 1}, 8, 1, 6, {'type': 'station', 'id': 'wood_station'}, result='plank', name='Plank (sawn)', desc='A saw wastes less than an axe.'),
 R('nails', 'workbench', {'scrap_metal': 1}, 8, 1, 6, {'type': 'item', 'id': 'scrap_metal'}), R('stone_block', 'stone_station', {'stone': 2}, 12, 2, 1, {'type': 'station', 'id': 'stone_station'}),
 R('iron_ingot', 'furnace', {'iron_ore': 2, 'coal': 1}, 40, 3, 1, {'type': 'item', 'id': 'iron_ore'}), R('glass_pane', 'furnace', {'glass_shard': 2, 'branch': 2}, 25, 1, 1, {'type': 'station', 'id': 'furnace'}),
 R('hinge', 'workbench', {'scrap_metal': 1, 'bolt': 1}, 8, 1, 2, {'type': 'item', 'id': 'bolt'}), R('cloth', 'workbench', {'cord': 3}, 20, 1, 1, {'type': 'item', 'id': 'fiber'}),
 R('crate', 'hand', {'branch': 6, 'cord': 2}, 15, 2, cat='storage'), R('workbench', 'hand', {'branch': 6, 'stone': 2, 'cord': 2}, 30, 4, cat='station'), R('stone_station', 'workbench', {'stone': 8, 'plank': 2}, 30, 5, cat='station', unlock={'type': 'station', 'id': 'workbench'}),
 R('wood_station', 'workbench', {'plank': 6, 'nails': 4, 'scrap_metal': 1}, 30, 4, cat='station', unlock={'type': 'station', 'id': 'workbench'}), R('furnace', 'stone_station', {'stone_block': 8, 'branch': 4}, 60, 6, cat='station', unlock={'type': 'station', 'id': 'stone_station'}),
 R('adv_bench', 'wood_station', {'plank': 8, 'iron_ingot': 2, 'rusted_gear': 1}, 60, 6, cat='station', unlock={'type': 'item', 'id': 'iron_ingot'}), R('chest', 'workbench', {'plank': 6, 'nails': 4, 'hinge': 1}, 25, 2, cat='storage', unlock={'type': 'station', 'id': 'workbench'}),
 R('chest_big', 'adv_bench', {'plank': 10, 'iron_ingot': 1, 'hinge': 2}, 40, 3, cat='storage', unlock={'type': 'station', 'id': 'adv_bench'}),
 R('bed_rustic', 'workbench', {'plank': 6, 'moss': 4, 'cord': 2}, 40, 3, cat='furniture', unlock={'type': 'station', 'id': 'workbench'}), R('bed_cottage', 'wood_station', {'plank': 6, 'cloth': 3}, 45, 3, cat='furniture', unlock={'type': 'item', 'id': 'cloth'}),
 R('table_rustic', 'workbench', {'plank': 4, 'nails': 2}, 20, 2, cat='furniture', unlock={'type': 'station', 'id': 'workbench'}), R('table_stone', 'stone_station', {'stone_block': 2, 'plank': 2}, 25, 3, cat='furniture', unlock={'type': 'station', 'id': 'stone_station'}),
 R('table_industrial', 'adv_bench', {'scrap_metal': 3, 'plank': 2, 'bolt': 2}, 25, 2, cat='furniture', unlock={'type': 'station', 'id': 'adv_bench'}), R('table_cottage', 'wood_station', {'plank': 4, 'cloth': 1}, 25, 2, cat='furniture', unlock={'type': 'item', 'id': 'cloth'}),
 R('chair_rustic', 'workbench', {'plank': 2, 'nails': 1}, 12, 1, cat='furniture', unlock={'type': 'station', 'id': 'workbench'}), R('chair_cottage', 'wood_station', {'plank': 2, 'cloth': 1}, 15, 1, cat='furniture', unlock={'type': 'item', 'id': 'cloth'}),
 R('shelf', 'workbench', {'plank': 5, 'nails': 3}, 20, 2, cat='furniture', unlock={'type': 'station', 'id': 'workbench'}), R('bookshelf', 'wood_station', {'plank': 6, 'nails': 3, 'feather': 1}, 30, 2, cat='furniture', unlock={'type': 'station', 'id': 'wood_station'}),
 R('cabinet', 'wood_station', {'plank': 6, 'hinge': 2}, 30, 2, cat='furniture', unlock={'type': 'station', 'id': 'wood_station'}), R('rug_woven', 'workbench', {'cloth': 3, 'poppy': 1}, 30, 1, cat='furniture', unlock={'type': 'item', 'id': 'cloth'}), R('rug_moss', 'workbench', {'cloth': 2, 'moss': 3}, 25, 1, cat='furniture', unlock={'type': 'item', 'id': 'cloth'}),
 R('floor_lamp', 'workbench', {'plank': 2, 'cloth': 1, 'glass_shard': 1}, 20, 1, cat='lighting', unlock={'type': 'item', 'id': 'cloth'}), R('table_lantern', 'workbench', {'scrap_metal': 1, 'glass_shard': 1}, 15, 1, cat='lighting', unlock={'type': 'item', 'id': 'glass_shard'}),
 R('potted_fern', 'hand', {'clay': 1, 'moss': 1}, 8, 0, cat='decor', unlock={'type': 'item', 'id': 'clay'}), R('painting', 'workbench', {'plank': 1, 'cloth': 1, 'daisy': 1}, 20, 0, cat='decor', unlock={'type': 'item', 'id': 'cloth'}), R('wall_shelf', 'workbench', {'plank': 2, 'nails': 2}, 10, 1, cat='decor', unlock={'type': 'station', 'id': 'workbench'}),
 R('stove', 'stone_station', {'stone_block': 6, 'scrap_metal': 2}, 45, 4, cat='kitchen', unlock={'type': 'station', 'id': 'stone_station'}), R('counter', 'wood_station', {'plank': 4, 'stone_block': 1}, 25, 2, cat='kitchen', unlock={'type': 'station', 'id': 'wood_station'}), R('healing_tonic', 'hand', {'moondew': 1, 'mint': 1}, 6, 0, cat='medicine', unlock={'type': 'item', 'id': 'moondew'}), R('ghost_salve', 'workbench', {'ghostcap': 1, 'moss': 2}, 12, 0, cat='medicine', unlock={'type': 'item', 'id': 'ghostcap'}),
 R('spore_jar', 'workbench', {'luminous_spores': 2, 'glass_shard': 1}, 15, 0, cat='lighting', unlock={'type': 'item', 'id': 'luminous_spores'}),
 R('rod_wooden', 'hand', {'branch': 3, 'cord': 2}, 15, 1, cat='tackle'), R('rod_improved', 'workbench', {'plank': 2, 'cord': 3, 'wire': 1}, 30, 2, cat='tackle', unlock={'type': 'station', 'id': 'workbench'}), R('rod_reinforced', 'workbench', {'plank': 2, 'iron_ingot': 1, 'wire': 2, 'resin': 1}, 45, 3, cat='tackle', unlock={'type': 'item', 'id': 'iron_ingot'}), R('rod_specialist', 'adv_bench', {'hardwood': 2, 'resin': 3, 'moonstone': 1, 'iron_ingot': 2}, 90, 5, cat='tackle', unlock={'type': 'item', 'id': 'moonstone'}),
 R('line_braided', 'hand', {'cord': 3}, 8, 0, cat='tackle'), R('line_wire', 'workbench', {'wire': 2, 'cord': 1}, 12, 0, cat='tackle', unlock={'type': 'item', 'id': 'wire'}), R('hook_iron', 'workbench', {'scrap_metal': 1}, 6, 0, cat='tackle', unlock={'type': 'station', 'id': 'workbench'}), R('hook_barbed', 'workbench', {'iron_ingot': 1}, 10, 0, cat='tackle', unlock={'type': 'item', 'id': 'iron_ingot'}), R('float_quill', 'hand', {'feather': 1, 'cord': 1}, 4, 0, cat='tackle', unlock={'type': 'item', 'id': 'feather'}),
 R('baitfish', 'hand', {'minnow': 1}, 2, 0, 2, cat='tackle', unlock={'type': 'item', 'id': 'minnow'}), R('dough_bait', 'hand', {'seeds_wild': 1, 'mushroom_brown': 1}, 4, 0, 4, cat='tackle', unlock={'type': 'item', 'id': 'seeds_wild'}), R('night_bait', 'hand', {'worm': 2, 'moondew': 1}, 4, 0, 3, cat='tackle', unlock={'type': 'item', 'id': 'moondew'}),
 R('lure_spinner', 'workbench', {'scrap_metal': 1, 'wire': 1}, 15, 1, cat='tackle', unlock={'type': 'item', 'id': 'wire'}), R('lure_fly', 'hand', {'feather': 2, 'cord': 1}, 10, 0, cat='tackle', unlock={'type': 'item', 'id': 'feather'}), R('lure_moth', 'workbench', {'lantern_moth': 1, 'wire': 1}, 15, 1, cat='tackle', unlock={'type': 'item', 'id': 'lantern_moth'}), R('lure_glow', 'workbench', {'luminous_spores': 2, 'nightglass': 1, 'wire': 1}, 25, 2, cat='tackle', unlock={'type': 'item', 'id': 'nightglass'}),
 R('garden_bed', 'workbench', {'plank': 4, 'clay': 2}, 25, 3, cat='garden', unlock={'type': 'station', 'id': 'workbench'}),
]
NAMES = {'crate': ('Crate', 'Rough slats lashed tight. Holds what you cannot carry.'), 'workbench': ('Workbench', 'A plank top, a vise, and the first real tool you own.'), 'stone_station': ('Stoneworking block', 'A low boulder dressed flat, for squaring stone.'),
 'wood_station': ('Sawhorses', 'Two trestles and a saw: boards come cleaner here.'), 'furnace': ('Smelting furnace', 'A stone dome and a hot mouth. Ore goes in, metal comes out.'), 'adv_bench': ('Advanced workbench', 'Salvaged drawers, a working gear train, and a lamp that still glows.'),
 'chest': ('Chest', 'Iron-strapped, with a lock that mostly works.'), 'chest_big': ('Large chest', 'For a household, not a camp.'), 'bed_rustic': ('Moss-stuffed bed', 'A real frame and a soft mattress of dried moss.'), 'bed_cottage': ('Cottage bed', 'A quilt, at last.'),
 'table_rustic': ('Rustic table', 'Planks and pegs.'), 'table_stone': ('Stone-top table', 'Cold in the morning, solid forever.'), 'table_industrial': ('Salvage table', 'A steel frame with a weathered top.'), 'table_cottage': ('Cottage table', 'A cloth makes it a home.'),
 'chair_rustic': ('Ladderback chair', 'Honest and slightly crooked.'), 'chair_cottage': ('Cushioned chair', 'A little blue cushion.'), 'shelf': ('Shelves', 'A place for jars and small finds.'), 'bookshelf': ('Bookshelf', 'For what you write down and what you rescue.'), 'cabinet': ('Cabinet', 'Two panelled doors on proper hinges.'),
 'rug_woven': ('Woven rug', 'Red and gold, dyed with poppies.'), 'rug_moss': ('Moss-green rug', 'Quiet colours from the woods.'), 'floor_lamp': ('Floor lamp', 'Warm light behind a cloth shade.'), 'table_lantern': ('Small lantern', 'A little flame in old glass.'), 'potted_fern': ('Potted fern', 'A piece of the forest indoors.'),
 'painting': ('Painted landscape', 'Your clearing, more or less.'), 'wall_shelf': ('Wall shelf', 'Hangs on a wall face.'), 'stove': ('Cookstove', 'Stone body, iron flue. Cooking comes later; the warmth is now.'), 'counter': ('Kitchen counter', 'Stone top on a wooden base.'), 'spore_jar': ('Spore jar', 'Cold light that never needs oil. Stalkers do not mind it, but you might.'), 'garden_bed': ('Raised garden bed', 'Ready for planting when seeds can be sown.')}
for r in RECIPES:
    if not r['name'] and r['id'] in NAMES: r['name'], r['description'] = NAMES[r['id']]
    if not r['name']: m = next(i for i in MATERIALS + NIGHT_ITEMS + TACKLE_ITEMS + FISH_ITEMS if i['id'] == r['id']); r['name'], r['description'] = m['name'], m['description']
PLACEABLE_ITEMS = [I(k, NAMES[k][0], NAMES[k][1], 5, 8, 3, sprite=k) for k in NAMES]
CRAFTED_ITEMS = MATERIALS + PLACEABLE_ITEMS + NIGHT_ITEMS + TACKLE_ITEMS + FISH_ITEMS + FEST_ITEMS
L_CRATE = dict(slots=8)
def O(id, foot, **k): return dict(id=id, name=NAMES[id][0], cat=k.pop('cat', 'Home'), layer='object', item=id, sprite=id, foot=foot, durability=k.pop('durability', 60), **k)
LAMP = dict(radius=46, color=[1.0, 0.82, 0.55], intensity=0.95, kind='lantern')
C = [
 dict(id='fnd_wood', name='Wooden foundation', cat='Foundation', layer='foundation', mat='wood', cost={'plank': 1, 'branch': 1}, minutes=10, energy=1, durability=120, stage=2),
 dict(id='fnd_reinforced', name='Reinforced foundation', cat='Foundation', layer='foundation', mat='reinforced', cost={'plank': 2, 'nails': 2}, minutes=15, energy=2, durability=200, stage=3),
 dict(id='fnd_stone', name='Stone foundation', cat='Foundation', layer='foundation', mat='stone', cost={'stone': 2, 'clay': 1}, minutes=25, energy=3, durability=400, stage=4),
 dict(id='floor_plank', name='Plank floor', cat='Floor', layer='floor', sprite='floor_plank', cost={'plank': 1}, minutes=6, energy=1, durability=80, stage=2),
 dict(id='floor_flag', name='Flagstone floor', cat='Floor', layer='floor', sprite='floor_flag', cost={'stone_block': 1}, minutes=12, energy=2, durability=200, stage=3),
 dict(id='floor_tile', name='Cottage tile floor', cat='Floor', layer='floor', sprite='floor_tile', cost={'clay': 1, 'plank': 1}, minutes=12, energy=1, durability=120, stage=3),
 dict(id='wall_wood', name='Wooden wall', cat='Wall', layer='wall', mat='wood', cost={'plank': 2, 'nails': 1}, minutes=15, energy=2, durability=150, stage=2),
 dict(id='wall_cottage', name='Timber-frame wall', cat='Wall', layer='wall', mat='cottage', cost={'plank': 2, 'clay': 1}, minutes=25, energy=2, durability=170, stage=3),
 dict(id='wall_reinforced', name='Reinforced wall', cat='Wall', layer='wall', mat='reinforced', cost={'plank': 3, 'nails': 2, 'scrap_metal': 1}, minutes=40, energy=4, durability=300, stage=4),
 dict(id='wall_stone', name='Stone wall', cat='Wall', layer='wall', mat='stone', cost={'stone_block': 2, 'clay': 1}, minutes=90, energy=6, durability=500, stage=4),
 dict(id='wall_metal', name='Metal-plated wall', cat='Wall', layer='wall', mat='metal', cost={'plank': 2, 'scrap_metal': 2, 'bolt': 2}, minutes=70, energy=6, durability=450, stage=5),
 dict(id='door', name='Plank door', cat='Opening', layer='opening', kind='door', cost={'plank': 2, 'cord': 2}, minutes=15, energy=1, durability=80, stage=2),
 dict(id='door_hinged', name='Hinged door', cat='Opening', layer='opening', kind='door', cost={'plank': 3, 'hinge': 2}, minutes=20, energy=1, durability=160, stage=3),
 dict(id='window', name='Shuttered window', cat='Opening', layer='opening', kind='window', cost={'plank': 1, 'glass_shard': 1}, minutes=15, energy=1, durability=60, stage=2),
 dict(id='window_pane', name='Glazed window', cat='Opening', layer='opening', kind='window', cost={'plank': 1, 'glass_pane': 1}, minutes=15, energy=1, durability=90, stage=3),
 dict(id='window_nightglass', name='Nightglass window', cat='Opening', layer='opening', kind='window', cost={'plank': 1, 'nightglass': 1}, minutes=20, energy=1, durability=200, stage=4),
 dict(id='roof_thatch', name='Thatch roof', cat='Roof', layer='roof', mat='thatch', cost={'fiber': 2, 'branch': 1}, minutes=12, energy=2, durability=70, stage=2),
 dict(id='roof_shingle', name='Shingle roof', cat='Roof', layer='roof', mat='shingle', cost={'plank': 2, 'nails': 1}, minutes=20, energy=3, durability=140, stage=3),
 dict(id='roof_slate', name='Slate roof', cat='Roof', layer='roof', mat='slate', cost={'stone_block': 1, 'plank': 1}, minutes=40, energy=4, durability=320, stage=4),
 dict(id='roof_support', name='Roof support', cat='Roof', layer='object', sprite='roof_support', foot=[6, 4], cost={'plank': 2}, minutes=10, energy=1, durability=120, stage=2, support=True),
 dict(id='fence', name='Post-and-rail fence', cat='Defense', layer='fence', cost={'branch': 2, 'cord': 1}, minutes=8, energy=1, durability=60, stage=3),
 dict(id='gate', name='Field gate', cat='Defense', layer='fence', kind='gate', sprite='gate', cost={'plank': 2, 'cord': 1}, minutes=12, energy=1, durability=70, stage=3),
 dict(id='gate_reinforced', name='Reinforced gate', cat='Defense', layer='fence', kind='gate', sprite='rgate', cost={'plank': 4, 'scrap_metal': 2, 'hinge': 2}, minutes=45, energy=4, durability=260, stage=4),
 dict(id='barricade', name='Barricade', cat='Defense', layer='object', sprite='barricade', foot=[26, 6], cost={'log': 2, 'cord': 2}, minutes=25, energy=4, durability=180, stage=4),
 dict(id='spikes', name='Spiked barrier', cat='Defense', layer='object', sprite='spikes', foot=[26, 5], cost={'branch': 6, 'cord': 2}, minutes=25, energy=3, durability=120, stage=4),
 dict(id='watch_platform', name='Watch platform', cat='Defense', layer='object', sprite='watch_platform', foot=[28, 8], cost={'log': 4, 'plank': 6, 'nails': 6}, minutes=240, energy=14, durability=250, stage=4),
 dict(id='torch_post', name='Torch post', cat='Defense', layer='object', sprite='torch_post', foot=[4, 3], cost={'branch': 2, 'bark': 1}, minutes=6, energy=0, durability=30, stage=3, light=dict(radius=50, color=[1.0, 0.72, 0.42], intensity=0.95, kind='fire')),
 dict(id='stone_steps', name='Stone steps', cat='Floor', layer='object', ground=True, sprite='stone_steps', foot=[0, 0], cost={'stone': 3}, minutes=15, energy=2, durability=300, stage=3),
 O('workbench', [28, 6], station='workbench'), O('stone_station', [26, 6], station='stone_station'), O('wood_station', [28, 5], station='wood_station'), O('furnace', [24, 8], station='furnace', light=dict(radius=38, color=[1.0, 0.66, 0.36], intensity=0.9, kind='fire')), O('adv_bench', [28, 6], station='adv_bench'),
 O('crate', [12, 5], storage=dict(slots=8)), O('chest', [14, 6], storage=dict(slots=16)), O('chest_big', [18, 6], storage=dict(slots=32)),
 O('bed_rustic', [16, 18], sleep=True, side='bed_rustic_side', side_foot=[26, 8]), O('bed_cottage', [16, 18], sleep=True, side='bed_cottage_side', side_foot=[26, 8]),
 O('table_rustic', [20, 6]), O('table_stone', [20, 6]), O('table_industrial', [20, 6]), O('table_cottage', [20, 6]), O('chair_rustic', [8, 5]), O('chair_cottage', [8, 5]), O('shelf', [16, 5]), O('bookshelf', [16, 5]), O('cabinet', [16, 5]),
 O('rug_woven', [0, 0], ground=True), O('rug_moss', [0, 0], ground=True), O('floor_lamp', [6, 4], light=LAMP, toggle=True), O('table_lantern', [6, 3], light=dict(LAMP, radius=34), toggle=True), O('potted_fern', [8, 4]), O('spore_jar', [6, 3], light=dict(radius=30, color=[0.55, 0.95, 1.0], intensity=0.7, kind='glow')),
 O('painting', [0, 0], mount=True), O('wall_shelf', [0, 0], mount=True), O('stove', [18, 8], light=dict(radius=34, color=[1.0, 0.66, 0.36], intensity=0.8, kind='fire')), O('counter', [20, 6]), O('garden_bed', [26, 8]),
]
STAGES = {1: 'Temporary campsite', 2: 'Woodland shelter', 3: 'Established homestead', 4: 'Reinforced residence', 5: 'Fortified woodland estate'}
def write():
    d = os.path.join(ROOT, 'assets/build'); os.makedirs(d, exist_ok=True)
    json.dump({'recipes': RECIPES, 'stations': {'hand': 'By hand', 'workbench': 'Workbench', 'stone_station': 'Stoneworking block', 'wood_station': 'Sawhorses', 'furnace': 'Smelting furnace', 'adv_bench': 'Advanced workbench'}}, open(os.path.join(d, 'recipes.json'), 'w'), indent=1)
    json.dump({'components': C, 'stages': STAGES, 'session_minutes': 60, 'demolish_refund': 0.5, 'repair': {'minutes': 20, 'energy': 1, 'amount': 0.5}}, open(os.path.join(d, 'components.json'), 'w'), indent=1)
    print(len(RECIPES), 'recipes', len(C), 'components')
if __name__ == '__main__': write()
