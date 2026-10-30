"""Time-of-day atmosphere as palette grading.

For every season the day table (palette.lut(season)) is graded into six
keyframes — dawn, morning, noon, golden, twilight, night — each at a
season-specific hour (summer days are long, winter days short). The live
renderer blends the two nearest keyframes, so lighting changes continuously
and never as a tint laid over the picture: shadows, mids and highlights of
every family move on their own curves, and emissive families brighten as the
ambient light falls.

Weather grades (rain, fog, snowfall) are small additional table operations,
also defined here so the engine and the viewer agree.
"""
from __future__ import annotations
import colorsys, json, os
from .palette import PAL, FAMILIES, SEASON_OVERRIDES, NIGHT_OVERRIDES, lerp, clamp8

EMISSIVE = ('lantern_glass', 'tent_interior', 'fire', 'ember', 'firefly', 'eyes', 'glowshroom', 'moonlight')
SKY = ('haze_far', 'haze_near', 'mist')

# keyframe hours per season: dawn, morning, noon, golden, twilight, night
KEY_HOURS = {
    'spring': [5.5, 8.0, 13.0, 18.5, 20.0, 22.0],
    'summer': [4.5, 7.0, 13.0, 20.0, 21.5, 23.0],
    'autumn': [6.5, 9.0, 13.0, 17.0, 18.5, 20.5],
    'winter': [7.5, 10.0, 13.0, 15.5, 17.0, 19.0],
}
KEY_NAMES = ['dawn', 'morning', 'noon', 'golden', 'twilight', 'night']
# ambient darkness per keyframe: drives emissive brightness and light pools
DARKNESS = {'dawn': 0.45, 'morning': 0.0, 'noon': 0.0, 'golden': 0.12, 'twilight': 0.62, 'night': 1.0}

# grading presets: (shadow_key, shadow_t), (mid_key, mid_t), (high_key, high_t), value, saturation
PRESETS = {
    'dawn':     ((62, 70, 112), 0.30, (150, 130, 150), 0.14, (222, 190, 200), 0.22, 0.86, 0.82),
    'morning':  ((40, 60, 70), 0.08, (160, 180, 150), 0.05, (240, 244, 225), 0.10, 1.00, 0.96),
    'noon':     ((0, 0, 0), 0.0, (0, 0, 0), 0.0, (0, 0, 0), 0.0, 1.00, 1.00),
    'golden':   ((92, 58, 88), 0.28, (238, 168, 100), 0.22, (255, 204, 122), 0.40, 0.95, 1.08),
    'twilight': ((38, 44, 92), 0.44, (92, 100, 152), 0.32, (176, 164, 206), 0.26, 0.64, 0.78),
}

def _sat_val(rgb, sat, val):
    r, g, b = [v / 255 for v in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    r, g, b = colorsys.hls_to_rgb(h, min(1, l * val), min(1, s * sat))
    return (r * 255, g * 255, b * 255)

def grade(rgb, rank, nranks, preset):
    sk, st, mk, mt, hk, ht, val, sat = PRESETS[preset]
    c = _sat_val(rgb, sat, val)
    pos = rank / max(1, nranks - 1)             # 0 shadow .. 1 highlight
    w_sh = max(0.0, 1 - pos * 2); w_hi = max(0.0, pos * 2 - 1); w_mid = 1 - w_sh - w_hi
    c = lerp(c, sk, st * w_sh); c = lerp(c, mk, mt * w_mid); c = lerp(c, hk, ht * w_hi)
    return clamp8(c)

def keyframe(season, name):
    """Full palette table for one keyframe of one season."""
    day = PAL.lut(season, False); night = PAL.lut(season, True)
    dark = DARKNESS[name]
    out = [(0, 0, 0)]
    for i, (fam, rank) in enumerate(PAL.entries[1:], start=1):
        n = PAL.nranks(fam)
        if fam in EMISSIVE:
            out.append(lerp(day[i], night[i], dark)); continue
        if name == 'night':
            out.append(night[i]); continue
        c = grade(day[i], rank, n, name)
        if fam in SKY and name in ('twilight', 'dawn'):      # sky families take the key more strongly
            c = lerp(c, night[i], 0.35 if name == 'twilight' else 0.15)
        out.append(c)
    return out

def season_keyframes(season):
    return {'season': season, 'hours': KEY_HOURS[season], 'names': KEY_NAMES, 'darkness': [DARKNESS[n] for n in KEY_NAMES],
            'tables': [keyframe(season, n) for n in KEY_NAMES]}

def table_at(season, hour):
    """Blend the two nearest keyframes (wrapping over midnight)."""
    kf = season_keyframes(season)
    hs = kf['hours']; tabs = kf['tables']
    n = len(hs)
    for k in range(n):
        h0, h1 = hs[k], hs[(k + 1) % n] + (24 if k == n - 1 else 0)
        hh = hour + (24 if (k == n - 1 and hour < hs[0]) else 0)
        if h0 <= hh <= h1:
            t = (hh - h0) / (h1 - h0); t = t * t * (3 - 2 * t)
            a, b = tabs[k], tabs[(k + 1) % n]
            return [lerp(a[i], b[i], t) for i in range(len(a))], kf['darkness'][k] * (1 - t) + kf['darkness'][(k + 1) % n] * t
    return tabs[-1], 1.0

# weather grades applied on top of the time table (also mirrored in the viewer)
WEATHER = {
    'clear':      {'key': (0, 0, 0), 't': 0.0, 'val': 1.0, 'sat': 1.0, 'lift': 0},
    'light_rain': {'key': (96, 110, 128), 't': 0.14, 'val': 0.90, 'sat': 0.82, 'lift': 4},
    'heavy_rain': {'key': (82, 94, 116), 't': 0.26, 'val': 0.78, 'sat': 0.70, 'lift': 8},
    'fog':        {'key': (190, 200, 205), 't': 0.22, 'val': 0.96, 'sat': 0.78, 'lift': 18},
    'snow':       {'key': (210, 220, 232), 't': 0.12, 'val': 0.97, 'sat': 0.80, 'lift': 10},
    'wind':       {'key': (0, 0, 0), 't': 0.0, 'val': 1.0, 'sat': 0.97, 'lift': 0},
}

def export(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    json.dump({'entries': [{'family': f, 'rank': r} for (f, r) in PAL.entries], 'emissive': list(EMISSIVE),
               'canopy': ['oak', 'birch', 'pine', 'rowan', 'shrub', 'fern', 'reed', 'tall'], 'water': ['water'], 'sky': list(SKY)},
              open(os.path.join(out_dir, 'palette_entries.json'), 'w'))
    for s in KEY_HOURS:
        json.dump(season_keyframes(s), open(os.path.join(out_dir, f'{s}_keyframes.json'), 'w'))
    json.dump(WEATHER, open(os.path.join(out_dir, 'weather_grades.json'), 'w'), indent=1)
