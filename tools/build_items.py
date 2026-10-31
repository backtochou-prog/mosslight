"""Item database, tools, resource nodes, and original 12x12 icons for MOSSlight.
Writes assets/items/{items.json, tools.json, nodes.json, icons_idx.png, icons.json}.
Items are data; nothing here is hard-coded into gameplay scripts."""
import sys, os, json, random
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
from pixelart.canvas import Canvas
from pixelart.palette import PAL

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets/items'); os.makedirs(OUT, exist_ok=True)
R = PAL.ramp
RARITY = ['common', 'uncommon', 'rare', 'very_rare', 'exceptional', 'legendary']

def item(id, name, cat, rarity, desc, icon, stack=20, value=1, weight=0.2, method='hand', seasons='all', time='any', weather='any', habitat='', craft='', kind='material', tool=None):
    return dict(id=id, name=name, description=desc, category=cat, rarity=rarity, icon=icon, stack=stack, value=value, weight=weight,
                gathering=method, tool=tool, seasons=seasons, time=time, weather=weather, habitat=habitat, crafting=craft, collectible=kind)

ITEMS = [
 # ---- natural
 item('branch','Branch','natural','common','A dry branch, light and brittle. Kindling and the start of every build.',('stick','wood'),stack=30,method='hand',habitat='under trees, beside logs',craft='fuel, frames'),
 item('log','Log','natural','common','A section of trunk. Heavy; you need an axe to get one.',('log','wood'),stack=10,value=3,weight=2.0,method='axe',tool='axe',habitat='felled trees',craft='walls, planks'),
 item('hardwood','Hardwood','natural','uncommon','Dense old-oak heartwood. Takes an edge and a polish.',('log','wood_dark'),stack=10,value=8,weight=2.5,method='axe',tool='axe',habitat='old oaks',craft='tool handles, fine furniture'),
 item('bark','Bark','natural','common','Peeled bark, curled at the edges. Good tinder; some kinds steep into tea.',('flake','wood'),stack=20,method='knife',tool='knife',habitat='birches, oaks',craft='tinder, dye'),
 item('fiber','Plant fibre','natural','common','Stringy fibres stripped from tall grass and reeds.',('bundle','reed'),stack=30,method='knife',tool='knife',habitat='tall grass, reed beds',craft='cord, nets'),
 item('vine','Vine','natural','common','A tough green vine, still supple.',('coil','moss'),stack=20,value=2,method='knife',tool='knife',habitat='ruins, old walls',craft='lashings'),
 item('resin','Plant resin','natural','uncommon','Amber beads of resin wept from a wounded pine. Sticky, fragrant.',('drop','flower_y'),stack=15,value=4,method='knife',tool='knife',habitat='pines',craft='glue, torches'),
 item('feather','Feather','natural','uncommon','A grey-brown flight feather, barbs still neat.',('feather','stone'),stack=20,value=2,weight=0.01,method='hand',habitat='meadow edges, below roosts',craft='fletching, quills'),
 item('antler','Shed antler','natural','rare','A shed antler, gnawed at the tip by something small.',('antler','canvas'),stack=5,value=12,weight=0.8,method='hand',seasons='spring',habitat='forest floor in spring',craft='handles, buttons'),
 item('eggshell','Empty eggshell','natural','uncommon','Half a speckled shell, long hatched.',('shell','flower_w'),stack=10,value=1,weight=0.01,method='hand',seasons='spring,summer',habitat='under hedges'),
 # ---- geological
 item('stone','Stone','geological','common','A fist-sized stone. The forest has no shortage.',('rock','stone'),stack=30,weight=0.8,method='hand',habitat='outcrops, path edges',craft='fire rings, foundations'),
 item('flint','Flint','geological','uncommon','Dark glassy flint. Strike it and it sparks.',('rock','metal'),stack=20,value=3,weight=0.4,method='hand',habitat='stream beds, outcrops',craft='fire starter, blades'),
 item('clay','Clay','geological','common','Cool grey clay from the pond bank. Keeps the shape you press into it.',('lump','mud'),stack=20,value=1,weight=1.0,method='hand',weather='rain,after_rain',habitat='pond banks after rain',craft='pots, bricks'),
 item('coal','Coal','geological','uncommon','A lump of coal. Burns long and hot.',('rock','wood_dark'),stack=20,value=4,weight=0.6,method='pickaxe',tool='pickaxe',habitat='dark seams in rock',craft='fuel, smelting'),
 item('copper_ore','Copper ore','geological','uncommon','Green-flecked rock with a dull metallic sheen.',('ore','moss'),stack=15,value=6,weight=1.2,method='pickaxe',tool='pickaxe',habitat='mineral deposits',craft='copper tools, wire'),
 item('iron_ore','Iron ore','geological','rare','Rust-red, heavy for its size.',('ore','metal_rust'),stack=15,value=10,weight=1.5,method='pickaxe',tool='pickaxe',habitat='deep deposits',craft='iron tools'),
 item('quartz','Quartz','geological','uncommon','A cloudy white crystal, cold to the touch.',('crystal','flower_w'),stack=15,value=5,weight=0.5,method='pickaxe',tool='pickaxe',habitat='mineral deposits',craft='lenses, decoration'),
 item('amethyst','Amethyst','geological','rare','Violet crystal points clustered on grey rock.',('crystal','flower_p'),stack=10,value=18,weight=0.5,method='pickaxe',tool='pickaxe',habitat='deposits, caves',craft='jewellery, lamps'),
 item('moonstone','Moonstone','geological','very_rare','Milky stone with a blue sheen that only shows under moonlight.',('crystal','moonlight'),stack=5,value=40,weight=0.4,method='pickaxe',tool='pickaxe',time='night',habitat='deposits, visible only at night',craft='lanterns, charms'),
 item('geode','Geode','geological','rare','A dull round stone. Heavier than it should be; something hollow inside.',('geode','stone'),stack=5,value=15,weight=1.0,method='pickaxe',tool='pickaxe',habitat='deposits'),
 # ---- botanical
 item('daisy','Meadow daisy','botanical','common','White petals, yellow heart. Grows wherever the sun reaches.',('flower','flower_w'),stack=20,method='hand',seasons='spring,summer',time='day',habitat='sunny meadow',craft='dye, posies',kind='plant'),
 item('bellflower','Bellflower','botanical','common','Nodding blue bells on a thin stem.',('flower','flower_b'),stack=20,value=2,method='hand',seasons='spring,summer',habitat='meadow edges',kind='plant'),
 item('poppy','Field poppy','botanical','uncommon','Crimson petals that bruise if you hold them too long.',('flower','berry'),stack=20,value=3,method='hand',seasons='summer',time='day',habitat='sunny meadow in summer',craft='red dye',kind='plant'),
 item('yarrow','Yarrow','botanical','uncommon','Feathery leaves and flat white heads. Stops bleeding, the old books say.',('herb','fern'),stack=15,value=4,method='knife',tool='knife',seasons='summer,autumn',habitat='dry meadow',craft='poultice',kind='plant'),
 item('mint','Wild mint','botanical','common','Square stems, cool smell. Grows where the ground stays damp.',('herb','moss'),stack=15,value=2,method='hand',seasons='spring,summer,autumn',habitat='pond margin',craft='tea',kind='plant'),
 item('rowan_berry','Rowan berries','botanical','common','Bitter orange-red berries in heavy clusters.',('berries','berry'),stack=30,value=2,method='hand',seasons='autumn',habitat='rowan trees in autumn',craft='jelly, bird bait',kind='plant'),
 item('blackberry','Blackberry','botanical','common','Sweet, staining, guarded by thorns.',('berries','flower_p'),stack=30,value=3,method='hand',seasons='summer,autumn',habitat='hedges and thickets',craft='jam',kind='plant'),
 item('burdock_root','Burdock root','botanical','uncommon','A long tap root, earthy and filling once boiled.',('root','dirt'),stack=10,value=3,weight=0.4,method='knife',tool='knife',seasons='autumn',habitat='disturbed ground near paths',kind='plant'),
 item('mushroom_brown','Brown cap','botanical','common','A plain brown mushroom. Safe, nutty, everywhere after rain.',('mushroom','dirt'),stack=20,value=2,method='hand',seasons='spring,autumn',weather='any',habitat='forest floor, near logs',craft='stew',kind='plant'),
 item('mushroom_red','Scarlet cap','botanical','uncommon','Red cap, white flecks. Beautiful, and not for eating.',('mushroom','shroom'),stack=10,value=5,method='hand',seasons='autumn',habitat='under birches',craft='dye, bait',kind='plant'),
 item('moss','Moss','botanical','common','A soft green pad of moss, damp underneath.',('pad','moss'),stack=20,method='hand',habitat='shaded stone, tree bases',craft='bedding, insulation',kind='plant'),
 item('seeds_wild','Wild seeds','botanical','common','A pinch of mixed meadow seed.',('seeds','worn'),stack=50,value=1,weight=0.01,method='hand',seasons='summer,autumn',habitat='dry seed heads',craft='planting',kind='plant'),
 item('fern_frond','Fern frond','botanical','common','A young curled frond.',('herb','fern'),stack=20,method='knife',tool='knife',seasons='spring',habitat='shade under trees',kind='plant'),
 item('nightlily','Night lily','botanical','rare','A pale lily that opens only after dark, on still water.',('flower','mist'),stack=10,value=12,method='hand',time='night',seasons='summer,autumn',habitat='pond shallows at night',craft='perfume, lamp oil',kind='plant'),
 # ---- abandoned world
 item('scrap_metal','Metal scrap','abandoned','common','A bent strip of old steel, orange with rust.',('scrap','metal_rust'),stack=20,value=3,weight=0.7,method='hand',habitat='ruins, roadsides',craft='nails, fittings',kind='artifact'),
 item('rusted_gear','Rusted gear','abandoned','uncommon','A toothed wheel from some machine. Still turns, grudgingly.',('gear','metal_rust'),stack=10,value=6,weight=0.5,method='hand',habitat='ruins',craft='mechanisms',kind='artifact'),
 item('wire','Copper wire','abandoned','uncommon','A tangle of green-tarnished wire.',('coil','moss'),stack=20,value=4,weight=0.1,method='hand',habitat='broken electronics',craft='electrics',kind='artifact'),
 item('circuit','Broken circuit board','abandoned','rare','Cracked green board, components still soldered on.',('board','moss'),stack=10,value=9,weight=0.2,method='hand',habitat='ruined buildings',craft='salvage',kind='artifact'),
 item('battery','Old battery','abandoned','uncommon','A cylinder with a faded label. Might hold a little charge.',('cylinder','metal'),stack=10,value=5,weight=0.3,method='hand',habitat='ruins, abandoned packs',craft='power',kind='artifact'),
 item('glass_shard','Glass fragment','abandoned','common','Sea-green glass, edges worn smooth by years of rain.',('shard','water'),stack=20,value=1,weight=0.1,method='hand',habitat='ruins, pond banks',craft='lenses, mosaics',kind='artifact'),
 item('bolt','Bolt and nut','abandoned','common','Still threaded together after all this time.',('bolt','metal'),stack=30,value=2,weight=0.1,method='hand',habitat='ruins',craft='fasteners',kind='artifact'),
 item('photo','Faded photograph','abandoned','rare','Two people on a dock, squinting at the sun. The pond behind them looks the same.',('card','canvas'),stack=1,value=0,weight=0.01,method='hand',habitat='inside the ruin',kind='keepsake'),
 item('key_old','Brass key','abandoned','very_rare','A small brass key on a loop of cord. Nothing here has a lock. Yet.',('key','lantern_glass'),stack=1,value=0,weight=0.05,method='hand',habitat='under the ruin lintel',kind='keepsake'),
 item('tin_cup','Tin cup','abandoned','uncommon','Dented, but it holds water.',('cup','metal'),stack=1,value=2,weight=0.2,method='hand',habitat='campsites, ruins',kind='keepsake'),
 # ---- rare discoveries
 item('moondew','Moondew','rare_find','very_rare','A luminous liquid that beads on glow-cap gills after dark. Fades by morning unless bottled.',('drop','glowshroom'),stack=10,value=35,weight=0.1,method='hand',time='night',habitat='glowing mushrooms after dark',craft='lamp oil, night tonics',kind='rare'),
 item('ghostcap','Ghostcap','rare_find','exceptional','A translucent mushroom that rises only in damp woods after midnight and is gone by dawn.',('mushroom','mist'),stack=5,value=60,weight=0.05,method='hand',time='deep_night',weather='after_rain,rain',seasons='autumn,spring',habitat='damp forest floor, after midnight, after rain',craft='rare remedies',kind='rare'),
 item('starshard','Starshard','rare_find','exceptional','A splinter of black mineral full of pinprick lights. Cold even in the sun.',('crystal','eyes'),stack=5,value=80,weight=0.3,method='pickaxe',tool='pickaxe',time='night',habitat='deposits under moonlight (caves, later)',craft='navigation, charms',kind='rare'),
 item('emberroot','Emberroot','rare_find','rare','A knotted root that stays warm in the hand. Grows where the ground is heated from below.',('root','fire'),stack=10,value=30,weight=0.3,method='knife',tool='knife',habitat='geothermal ground (future biome)',craft='warming salves, fuel',kind='rare'),
 item('lantern_moth','Lantern moth','rare_find','rare','A large pale moth drawn to lantern light. Its wing dust glows faintly.',('moth','mist'),stack=5,value=20,weight=0.01,method='hand',time='night',habitat='around lanterns at night',craft='glowing ink',kind='rare'),
 item('heartwood_seed','Heartwood seed','rare_find','legendary','A single seed from the oldest oak, found once in a lifetime among its roots. Plant it, and wait.',('seed','oak'),stack=1,value=0,weight=0.05,method='hand',seasons='autumn',time='night',weather='after_rain',habitat='roots of the great oak, one autumn night after rain',craft='a tree that remembers',kind='rare'),
]
TOOLS = [
 dict(id='hand', name='Bare hands', durability=None, compat=['hand'], efficiency=1.0, upgrade=None, icon=('hand','canvas'), description='Fingers and patience.'),
 dict(id='knife', name='Gathering knife', durability=60, compat=['hand','knife'], efficiency=1.1, upgrade='knife_steel', icon=('knife','metal'), description='A short, sharp blade for herbs, bark and fibre.'),
 dict(id='axe', name='Basic axe', durability=40, compat=['axe'], efficiency=1.0, upgrade='axe_copper', icon=('axe','wood'), description='A hatchet with a worn handle. For wood only.'),
 dict(id='pickaxe', name='Pickaxe', durability=40, compat=['pickaxe'], efficiency=1.0, upgrade='pickaxe_copper', icon=('pickaxe','metal'), description='Heavy, blunt, and the only way into rock.'),
 dict(id='rod', name='Fishing rod (placeholder)', durability=30, compat=['fishing'], efficiency=1.0, upgrade=None, icon=('rod','wood'), description='A reed rod and a length of line. Fishing comes later.'),
]
# ---- world resource nodes placed in the clearing. Each: visual kind + states, drop table, tool, conditions, respawn.
NODES = [
 dict(id='branches_log', kind='branch_pile', x=462, y=410, r=20, label='Gather branches', activity='gather_branches', tool='hand', drops=[['branch',2,3]], yields=2, respawn_hours=12, respawn_mode='time'),
 dict(id='branches_oak', kind='branch_pile', x=190, y=222, r=20, label='Gather branches', activity='gather_branches', tool='hand', drops=[['branch',1,3],['bark',0,1]], yields=2, respawn_hours=12, respawn_mode='time'),
 dict(id='branches_west', kind='branch_pile', x=150, y=334, r=20, label='Gather branches', activity='gather_branches', tool='hand', drops=[['branch',1,2]], yields=1, respawn_hours=18, respawn_mode='time'),
 dict(id='stones_outcrop', kind='stone_pile', x=338, y=238, r=22, label='Gather stones', activity='gather_stones', tool='hand', drops=[['stone',2,3],['flint',0,1]], yields=3, respawn_hours=36, respawn_mode='time'),
 dict(id='stones_path', kind='stone_pile', x=520, y=292, r=18, label='Gather stones', activity='gather_stones', tool='hand', drops=[['stone',1,2]], yields=2, respawn_hours=36, respawn_mode='time'),
 dict(id='mush_log', kind='mushroom', x=500, y=416, r=16, label='Pick mushrooms', activity='pick_plant', tool='hand', drops=[['mushroom_brown',1,2]], yields=1, respawn_hours=48, respawn_mode='time', seasons='spring,autumn'),
 dict(id='mush_north', kind='mushroom', x=432, y=142, r=16, label='Pick mushrooms', activity='pick_plant', tool='hand', drops=[['mushroom_brown',1,1],['mushroom_red',0,1]], yields=1, respawn_hours=48, respawn_mode='time', seasons='spring,autumn'),
 dict(id='daisies_s', kind='flower_w', x=386, y=352, r=16, label='Pick daisies', activity='pick_plant', tool='hand', drops=[['daisy',1,2]], yields=2, respawn_hours=72, respawn_mode='season', seasons='spring,summer', time='day'),
 dict(id='bells_e', kind='flower_b', x=470, y=234, r=16, label='Pick bellflowers', activity='pick_plant', tool='hand', drops=[['bellflower',1,2]], yields=2, respawn_hours=72, respawn_mode='season', seasons='spring,summer'),
 dict(id='poppies_se', kind='flower_r', x=606, y=372, r=16, label='Pick poppies', activity='pick_plant', tool='hand', drops=[['poppy',1,2]], yields=2, respawn_hours=72, respawn_mode='season', seasons='summer', time='day'),
 dict(id='berries_hedge', kind='berry_bush', x=560, y=440, r=20, label='Pick blackberries', activity='pick_plant', tool='hand', drops=[['blackberry',2,4]], yields=3, respawn_hours=96, respawn_mode='season', seasons='summer,autumn'),
 dict(id='rowan_berries', kind='berry_rowan', x=418, y=184, r=18, label='Pick rowan berries', activity='pick_plant', tool='hand', drops=[['rowan_berry',2,3]], yields=2, respawn_hours=120, respawn_mode='season', seasons='autumn'),
 dict(id='mint_pond', kind='herb', x=600, y=352, r=16, label='Cut wild mint', activity='cut_herb', tool='knife', drops=[['mint',1,2]], yields=2, respawn_hours=48, respawn_mode='time', seasons='spring,summer,autumn'),
 dict(id='fiber_reeds', kind='herb', x=690, y=330, r=18, label='Cut reed fibre', activity='cut_herb', tool='knife', drops=[['fiber',2,3]], yields=3, respawn_hours=24, respawn_mode='time'),
 dict(id='vines_ruin', kind='vine', x=556, y=136, r=18, label='Cut vines', activity='cut_herb', tool='knife', drops=[['vine',1,2]], yields=2, respawn_hours=72, respawn_mode='time'),
 dict(id='moss_stone', kind='moss_pad', x=352, y=236, r=14, label='Gather moss', activity='pick_plant', tool='hand', drops=[['moss',1,2]], yields=2, respawn_hours=72, respawn_mode='time'),
 dict(id='oak_wood', kind='tree_marker', x=216, y=214, r=22, label='Chop the oak', activity='cut_tree', tool='axe', drops=[['log',1,1],['hardwood',0,1]], yields=4, respawn_hours=240, respawn_mode='time'),
 dict(id='deposit_ruin', kind='deposit', x=664, y=146, r=20, label='Mine the deposit', activity='mine', tool='pickaxe', drops=[['stone',1,1],['copper_ore',1,2],['quartz',0,1],['coal',0,1]], yields=5, respawn_hours=None, respawn_mode='none', night_extra=[['moonstone',0,1]]),
 dict(id='deposit_west', kind='deposit', x=96, y=352, r=20, label='Mine the deposit', activity='mine', tool='pickaxe', drops=[['stone',1,2],['iron_ore',0,1],['amethyst',0,1],['geode',0,1]], yields=4, respawn_hours=None, respawn_mode='none'),
 dict(id='scrap_ruin', kind='scrap_pile', x=676, y=112, r=18, label='Search the rubble', activity='search', tool='hand', drops=[['scrap_metal',1,2],['bolt',0,2],['glass_shard',0,1],['rusted_gear',0,1],['battery',0,1]], yields=3, respawn_hours=None, respawn_mode='none'),
 dict(id='scrap_beam', kind='scrap_pile', x=606, y=130, r=16, label='Search under the beam', activity='search', tool='hand', drops=[['wire',0,2],['circuit',0,1],['photo',0,1],['tin_cup',0,1]], yields=2, respawn_hours=None, respawn_mode='none', unique=['photo','tin_cup']),
 dict(id='lintel_key', kind='hidden', x=612, y=98, r=14, label='Feel along the lintel', activity='search', tool='hand', drops=[['key_old',1,1]], yields=1, respawn_hours=None, respawn_mode='none', unique=['key_old']),
 # nocturnal / conditional
 dict(id='moondew_ruin', kind='glowcap', x=596, y=134, r=16, label='Collect moondew', activity='pick_plant', tool='hand', drops=[['moondew',1,1]], yields=1, respawn_hours=24, respawn_mode='time', time='night'),
 dict(id='moondew_log', kind='glowcap', x=500, y=408, r=16, label='Collect moondew', activity='pick_plant', tool='hand', drops=[['moondew',1,1]], yields=1, respawn_hours=24, respawn_mode='time', time='night'),
 dict(id='ghostcap_forest', kind='ghostcap', x=132, y=214, r=16, label='Pick the ghostcap', activity='pick_plant', tool='hand', drops=[['ghostcap',1,1]], yields=1, respawn_hours=72, respawn_mode='time', time='deep_night', weather='after_rain,rain', seasons='spring,autumn'),
 dict(id='nightlily_pond', kind='nightlily', x=640, y=300, r=18, label='Pick the night lily', activity='pick_plant', tool='hand', drops=[['nightlily',1,1]], yields=1, respawn_hours=48, respawn_mode='time', time='night', seasons='summer,autumn'),
 dict(id='moth_lantern', kind='moth', x=244, y=256, r=16, label='Catch the moth', activity='pick_plant', tool='hand', drops=[['lantern_moth',1,1]], yields=1, respawn_hours=24, respawn_mode='time', time='night'),
 dict(id='heartwood', kind='hidden', x=206, y=216, r=14, label='Search among the roots', activity='search', tool='hand', drops=[['heartwood_seed',1,1]], yields=1, respawn_hours=None, respawn_mode='none', time='night', seasons='autumn', weather='after_rain', unique=['heartwood_seed']),
 dict(id='clay_bank', kind='clay', x=572, y=222, r=16, label='Dig clay', activity='gather_stones', tool='hand', drops=[['clay',1,2]], yields=3, respawn_hours=24, respawn_mode='time', weather='rain,after_rain'),
 dict(id='feather_meadow', kind='feather', x=360, y=120, r=14, label='Pick up the feather', activity='search', tool='hand', drops=[['feather',1,1]], yields=1, respawn_hours=36, respawn_mode='time'),
]
# ---------------- icons: 12x12, drawn from (shape, family)
def icon(shape, fam):
    c = Canvas(12, 12)
    from pixelart.palette import FAMILIES
    r = R(fam) if fam in FAMILIES else R('wood')
    if fam == 'wood_dark': r = R('wood')[:4]
    n = len(r); lo, mid, hi = r[max(0, n - 4)], r[max(0, n - 3)], r[n - 2]; dk = r[0]
    w = R('wood'); st = R('stone')
    if shape == 'stick': c.line(2, 9, 9, 2, mid); c.line(3, 9, 10, 2, lo); c.put(5, 5, hi); c.put(8, 4, hi)
    elif shape == 'log': c.rect(2, 4, 8, 5, mid); c.rect(2, 4, 8, 1, hi); c.rect(2, 8, 8, 1, lo); c.ellipse(9.5, 6, 1.5, 2.5, hi); c.put(9, 6, lo)
    elif shape == 'flake': c.poly([(2, 3), (9, 2), (10, 8), (3, 10)], mid); c.line(3, 4, 8, 3, hi); c.line(4, 9, 9, 8, lo)
    elif shape == 'bundle':
        for i in range(4): c.vline(3 + i * 2, 2 + (i % 2), 10, mid if i % 2 else hi)
        c.hline(2, 10, 6, lo); c.put(6, 6, dk)
    elif shape == 'coil': c.ellipse(6, 6, 4, 3.5, mid); c.ellipse(6, 6, 2, 1.8, 0); c.ellipse(6, 5, 3.5, 2.5, hi); c.ellipse(6, 5.5, 2, 1.5, 0); c.put(2, 7, lo)
    elif shape == 'drop': c.poly([(6, 1), (9.5, 7), (6, 10.5), (2.5, 7)], mid); c.ellipse(6, 7, 3, 3, mid); c.put(4, 6, hi); c.put(5, 5, hi); c.put(8, 8, lo)
    elif shape == 'feather': c.line(2, 10, 9, 3, mid); c.poly([(3, 9), (9, 2), (10, 5), (6, 9)], hi); c.line(3, 9, 8, 4, lo)
    elif shape == 'antler': c.line(3, 10, 6, 4, mid); c.line(6, 4, 8, 2, mid); c.line(5, 6, 3, 3, mid); c.line(6, 4, 9, 5, hi)
    elif shape == 'shell': c.ellipse(6, 7, 4, 3, hi); c.rect(2, 2, 8, 5, 0); c.poly([(2, 7), (3, 4), (5, 6), (6, 3), (8, 6), (10, 4), (10, 7)], hi); c.put(4, 8, mid); c.put(7, 9, mid)
    elif shape == 'rock': c.ellipse(6, 7, 4.5, 3.5, mid); c.ellipse(5, 6, 2.5, 1.8, hi); c.hline(3, 9, 10, lo); c.put(9, 8, lo)
    elif shape == 'lump': c.ellipse(6, 7, 4.5, 3.5, mid); c.put(4, 6, hi); c.put(5, 5, hi); c.hline(3, 9, 10, lo)
    elif shape == 'ore': c.ellipse(6, 7, 4.5, 3.5, st[2]); c.hline(3, 9, 10, st[0]); c.put(4, 6, mid); c.put(5, 6, hi); c.put(7, 8, mid); c.put(8, 5, hi); c.put(3, 8, mid)
    elif shape == 'crystal': c.poly([(6, 1), (9, 6), (7, 11), (5, 11), (3, 6)], mid); c.line(6, 2, 4, 6, hi); c.put(6, 3, hi); c.line(8, 7, 7, 10, lo); c.hline(4, 8, 11, st[0])
    elif shape == 'geode': c.ellipse(6, 6, 4.5, 4, st[2]); c.ellipse(6, 6, 2.5, 2.2, R('flower_p')[1]); c.put(6, 5, R('flower_p')[2]); c.put(3, 8, st[0])
    elif shape == 'flower':
        g = R('grass'); c.vline(6, 6, 11, g[2]); c.put(5, 9, g[3])
        for dx, dy in ((0, -2), (-2, 0), (2, 0), (0, 2)): c.rect(5 + dx, 3 + dy, 2, 2, mid)
        c.rect(5, 3, 2, 2, hi); c.put(5, 3, R('flower_y')[1] if fam in ('flower_w', 'mist') else dk)
    elif shape == 'herb':
        c.vline(6, 3, 11, lo)
        for i, y in enumerate((3, 5, 7)): c.put(5 - i // 2, y, mid); c.put(4 - i // 2, y, hi); c.put(7 + i // 2, y + 1, mid); c.put(8 + i // 2, y + 1, hi)
    elif shape == 'berries':
        g = R('grass'); c.put(5, 2, g[2]); c.put(6, 3, g[3]); c.put(7, 2, g[2])
        for (x, y) in ((4, 6), (7, 5), (6, 8), (3, 9), (8, 8)): c.ellipse(x, y, 1.5, 1.5, mid); c.put(x - 1, y - 1, hi)
    elif shape == 'root': c.line(6, 2, 5, 10, mid); c.line(7, 2, 6, 10, lo); c.line(5, 6, 3, 9, mid); c.line(7, 5, 9, 8, mid); c.put(6, 3, hi); c.put(4, 1, R('grass')[3]); c.put(6, 1, R('grass')[3])
    elif shape == 'mushroom': ss = R('shroom_stem'); c.rect(5, 6, 2, 5, ss[1]); c.put(6, 6, ss[0]); c.ellipse(6, 5, 4, 2.5, mid); c.put(4, 4, hi); c.put(7, 4, hi); c.hline(3, 9, 7, lo)
    elif shape == 'pad': c.ellipse(6, 7, 4.5, 2.5, mid); c.ellipse(5, 6, 2.5, 1.5, hi); c.hline(3, 9, 9, lo); c.put(8, 8, lo)
    elif shape == 'seeds':
        for (x, y) in ((3, 4), (6, 3), (8, 5), (4, 7), (7, 8), (5, 9)): c.put(x, y, mid); c.put(x + 1, y, lo)
    elif shape == 'seed': c.ellipse(6, 6, 2.5, 3.5, w[3]); c.put(5, 4, w[4]); c.put(6, 2, R('grass')[4]); c.put(7, 1, R('grass')[3])
    elif shape == 'scrap': c.poly([(2, 4), (10, 2), (10, 5), (3, 8)], mid); c.line(3, 7, 9, 4, lo); c.put(4, 5, hi); c.line(4, 9, 9, 8, R('metal')[2])
    elif shape == 'gear': mt = R('metal'); c.ellipse(6, 6, 4, 4, mid); c.ellipse(6, 6, 1.5, 1.5, 0); [c.put(x, y, mid) for (x, y) in ((6, 1), (6, 11), (1, 6), (11, 6), (2, 2), (10, 2), (2, 10), (10, 10))]; c.put(4, 4, hi)
    elif shape == 'board': mt = R('metal'); c.rect(2, 3, 8, 7, mid); c.rect(2, 3, 8, 1, hi); c.rect(4, 5, 2, 2, mt[1]); c.rect(7, 6, 2, 1, mt[3]); c.put(3, 8, mt[3]); c.put(8, 8, mt[3])
    elif shape == 'cylinder': c.rect(4, 2, 4, 8, mid); c.rect(4, 2, 1, 8, hi); c.rect(7, 2, 1, 8, lo); c.rect(5, 1, 2, 1, R('metal_rust')[2]); c.hline(4, 7, 6, R('metal')[0])
    elif shape == 'shard': c.poly([(3, 2), (9, 4), (7, 10), (4, 8)], mid); c.line(4, 3, 8, 5, hi); c.put(6, 7, lo)
    elif shape == 'bolt': c.rect(5, 2, 2, 8, mid); c.rect(4, 4, 4, 2, hi); c.put(5, 3, hi); c.put(6, 9, lo); c.put(4, 5, lo)
    elif shape == 'card': c.rect(2, 2, 8, 9, R('canvas')[5]); c.rect(3, 3, 6, 5, R('water')[4]); c.rect(3, 6, 6, 2, R('wood')[3]); c.put(5, 5, R('canvas')[3]); c.put(7, 5, R('canvas')[3])
    elif shape == 'key': c.ellipse(4, 4, 2.5, 2.5, mid); c.ellipse(4, 4, 1, 1, 0); c.line(6, 6, 10, 10, mid); c.put(9, 8, mid); c.put(10, 8, mid); c.put(3, 3, hi)
    elif shape == 'cup': mt = R('metal'); c.rect(3, 3, 6, 7, mt[2]); c.rect(3, 3, 6, 1, mt[3]); c.rect(3, 9, 6, 1, mt[1]); c.put(9, 5, mt[2]); c.put(9, 6, mt[2]); c.put(4, 5, mt[3])
    elif shape == 'moth': c.poly([(1, 4), (6, 6), (1, 9)], mid); c.poly([(11, 4), (6, 6), (11, 9)], mid); c.rect(5, 3, 2, 7, lo); c.put(3, 5, hi); c.put(9, 5, hi); c.put(5, 2, dk); c.put(7, 2, dk)
    elif shape == 'hand': c.rect(4, 5, 5, 5, mid); c.rect(3, 2, 1, 4, mid); c.rect(5, 1, 1, 5, mid); c.rect(7, 1, 1, 5, mid); c.rect(9, 3, 1, 4, mid); c.put(4, 6, hi)
    elif shape == 'knife': c.line(2, 10, 6, 6, w[2]); c.line(3, 10, 7, 6, w[1]); c.poly([(5, 5), (10, 1), (11, 3), (7, 7)], R('metal')[3]); c.line(6, 5, 10, 2, R('metal')[2]); c.put(10, 2, PAL.i('flower_w', 2))
    elif shape == 'axe': c.line(3, 10, 8, 4, w[3]); c.line(4, 10, 9, 4, w[1]); c.poly([(7, 2), (11, 3), (11, 7), (8, 6)], R('metal')[3]); c.line(8, 3, 10, 4, R('metal')[2]); c.put(11, 5, PAL.i('flower_w', 1))
    elif shape == 'pickaxe': c.line(3, 10, 8, 5, w[3]); c.line(4, 10, 9, 5, w[1]); c.line(4, 4, 11, 6, R('metal')[2]); c.line(5, 3, 11, 5, R('metal')[3]); c.put(4, 4, R('metal')[1]); c.put(11, 6, R('metal')[1])
    elif shape == 'rod': c.line(2, 10, 9, 2, w[3]); c.line(9, 2, 10, 7, R('canvas')[5]); c.put(10, 8, R('metal')[2])
    c.outline_inside(dk if shape not in ('flower', 'herb', 'seeds', 'feather') else r[0])
    return c

def build():
    names = [i['id'] for i in ITEMS] + ['tool_' + t['id'] for t in TOOLS]
    sheet = Canvas(12 * 10, 12 * ((len(names) + 9) // 10)); index = {}
    for k, (nm, ic) in enumerate([(i['id'], i['icon']) for i in ITEMS] + [('tool_' + t['id'], t['icon']) for t in TOOLS]):
        c = icon(*ic); x, y = (k % 10) * 12, (k // 10) * 12; sheet.blit(c, x, y); index[nm] = [x, y]
    Image.fromarray(sheet.a, 'L').save(os.path.join(OUT, 'icons_idx.png')); sheet.save(os.path.join(OUT, 'icons_preview.png'), scale=1)
    json.dump({'size': 12, 'cols': 10, 'index': index}, open(os.path.join(OUT, 'icons.json'), 'w'))
    for it in ITEMS: it['icon'] = it['id']
    for t in TOOLS: t['icon'] = 'tool_' + t['id']
    json.dump({'version': 1, 'rarities': RARITY, 'categories': ['natural', 'geological', 'botanical', 'abandoned', 'rare_find'], 'items': ITEMS}, open(os.path.join(OUT, 'items.json'), 'w'), indent=1)
    json.dump({'tools': TOOLS}, open(os.path.join(OUT, 'tools.json'), 'w'), indent=1)
    json.dump({'nodes': NODES, 'activities_extra': {'pick_plant': {'label': 'Pick', 'energy': 1, 'minutes': 4, 'heavy': False, 'anim': 'gather'},
               'cut_herb': {'label': 'Cut', 'energy': 1, 'minutes': 5, 'heavy': False, 'anim': 'gather'}, 'search': {'label': 'Search', 'energy': 1, 'minutes': 6, 'heavy': False, 'anim': 'gather'}}},
              open(os.path.join(OUT, 'nodes.json'), 'w'), indent=1)
    ids = [i['id'] for i in ITEMS]; assert len(ids) == len(set(ids))
    collectible = sorted({d[0] for n in NODES for d in n['drops'] + n.get('night_extra', [])})
    print(f'{len(ITEMS)} items, {len(TOOLS)} tools, {len(NODES)} nodes, {len(collectible)} items collectible in the clearing: {collectible}')
if __name__ == '__main__': build()
