"""Single source of balancing numbers for the survival clock. Writes
assets/survival/config.json, read by preview/survival.js and godot/survival/."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = {
    'version': 1,
    'energy': {'max': 100, 'start': 100, 'walk_per_game_hour': 1.0,
               'states': [['energetic', 75], ['tired', 40], ['exhausted', 15], ['critical', 1], ['zero', 0]],
               'efficiency': {'energetic': 1.0, 'tired': 1.0, 'exhausted': 0.6, 'critical': 0.4, 'zero': 0.0},
               'allow_heavy_when_exhausted': True, 'allow_heavy_when_critical': False},
    'schedule': {   # base rhythm (spring); shifted per season by that season's dawn/night keyframe hours
        'dawn': 6.0, 'day': 7.0, 'sunset': 17.0, 'early_night': 19.0, 'deep_night': 22.0, 'dawn_transition': 5.0,
        'reference_season': 'spring'},
    'sleep': {'wake_hour': 6.0, 'full_restore_before_hour': 2.0, 'short_night_restore': 80, 'fade_seconds': 1.2, 'cooldown_seconds': 1.5},
    'activities': {
        'inspect':         {'label': 'Inspect',        'energy': 0, 'minutes': 2,  'heavy': False, 'anim': None},
        'gather_branches': {'label': 'Gather branches','energy': 2, 'minutes': 6,  'heavy': False, 'anim': 'gather'},
        'gather_stones':   {'label': 'Gather stones',  'energy': 3, 'minutes': 8,  'heavy': False, 'anim': 'gather'},
        'fish_attempt':    {'label': 'Fish',           'energy': 2, 'minutes': 10, 'heavy': False, 'anim': 'fish'},
        'cut_tree':        {'label': 'Cut tree',       'energy': 8, 'minutes': 25, 'heavy': True,  'anim': 'build'},
        'mine':            {'label': 'Mine',           'energy': 6, 'minutes': 20, 'heavy': True,  'anim': 'build'},
        'build':           {'label': 'Build',          'energy': 5, 'minutes': 30, 'heavy': True,  'anim': 'build'},
        'tend_fire':       {'label': 'Tend the fire',  'energy': 1, 'minutes': 4,  'heavy': False, 'anim': 'gather'},
    },
    'danger': {'early_night': 0.4, 'deep_night': 1.0, 'day': 0.0, 'sunset': 0.1, 'dawn': 0.1, 'dawn_transition': 0.3},
}
os.makedirs(os.path.join(ROOT, 'assets/survival'), exist_ok=True)
json.dump(CONFIG, open(os.path.join(ROOT, 'assets/survival/config.json'), 'w'), indent=1)
print('survival config written')
