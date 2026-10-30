"""MOSSlight master palette.

Every asset is authored as an *indexed* image: each pixel stores a palette index,
never an RGB value. Index 0 is transparent. Each palette entry belongs to a
*family* (grass, dirt, oak canopy, ...) and has a *rank* inside that family's
ramp (0 = deepest shadow ... N = brightest highlight).

Atmosphere states (day, night, later: dusk, winter) are *lookups* from the same
indices. Night is therefore not a tint on top of day: each family is remapped
on its own terms, and emissive families (lantern glass, embers, tent interior,
fireflies, glow mushrooms) become the brightest thing in the frame.
"""
from __future__ import annotations
import colorsys

def _hex(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))

def clamp8(c):
    return tuple(max(0, min(255, int(round(v)))) for v in c)

# ---------------------------------------------------------------------------
# Day ramps. Shadows lean cool (blue/teal), highlights lean warm (yellow).
# Keep 5-7 steps per family so shading stays readable at 16 px.
# ---------------------------------------------------------------------------
FAMILIES: dict[str, list[str]] = {
    # terrain
    'grass':      ['1b3826', '2a5531', '3b733c', '539a44', '72b64c', '96cc58', 'bde06a'],
    'forest':     ['16302a', '20412f', '2c5736', '3a6e3d', '4a8446'],          # shaded forest floor
    'worn':       ['4b6a38', '63893f', '7ea249', '97b656', 'b0c865'],            # trampled dry grass
    'dirt':       ['3a2619', '5b3e28', '7b5736', '9b7349', 'b88f60', 'd2ad7c'],
    'stone':      ['2b2d38', '444854', '606473', '7f838f', '9ea2ac', 'bdc0c6'],
    'mud':        ['4c3d2e', '6a5742', '857055', '9f8a6b'],                      # wet shore band
    'water':      ['173a5a', '205386', '2b6fa8', '4090c4', '6ab4d8', 'a4d8ee', 'def4fb'],
    'moss':       ['3f6d2e', '5c8f36', '7fb043', 'a4cc55'],
    'leaf_litter':['5a3a26', '7d4f2d', '9f6b36', 'b8873f'],
    'pebble':     ['55596a', '7c808e', 'a3a7b0'],
    'sand':       ['7d6a4a', '9c8760', 'b9a47a', 'd1be92', 'e4d6ad'],
    'earth':      ['4a3b2e', '66523f', '836c55', '9e876c', 'b6a088'],       # packed earth
    'snow':       ['7d8ea6', '9fb0c4', 'c3d2e0', 'e2ebf3', 'f7fbff'],
    'ice':        ['5f7f98', '7f9fb5', 'a3c0d0', 'c8dde6', 'e6f2f6'],
    # vegetation
    'oak':        ['173320', '214d2a', '306b36', '3f8a41', '57a64a', '7dc258', 'a7d968'],
    'birch':      ['273f30', '3b6140', '52844a', '6ea553', '93c262', 'b9db78'],
    'pine':       ['102a26', '183f35', '215644', '2d7053', '3d8a61', '55a46f'],
    'rowan':      ['28492a', '3d6c38', '588f48', '76ac56', '99c766'],
    'berry':      ['7a1f22', 'c0392b', 'e8705b'],
    'shrub':      ['213e2b', '345c38', '488044', '62a04e', '83bb5b', 'a9d26d'],
    'fern':       ['24462c', '3a6d3b', '539047', '72b055', '96ca66'],
    'reed':       ['4a5f2a', '6a8236', '8ea745', 'b3c45a'],
    'lily':       ['2f5e3a', '48804a', '69a258', '8fbf6a'],
    'flower_w':   ['b9b4a6', 'ece6d6', 'fffaf0'],
    'flower_p':   ['8c5a86', 'c088b6', 'e5b3d6'],
    'flower_b':   ['3d4f8c', '6577bd', '9aa9dd'],
    'flower_y':   ['b98a2a', 'e9bf4c', 'f8e38a'],
    'shroom':     ['6e2f22', 'a8452f', 'd0674a', 'e3a080'],
    'shroom_stem':['9a8f7c', 'c9bfa9', 'eae2cf'],
    'glowshroom': ['5f7f88', '8fb3b8', 'bfe0dc'],   # pale by day, luminous by night
    # distant / atmosphere
    'haze_far':   ['6f8d86', '829f98', '95b1a8'],
    'haze_near':  ['4b7659', '5c8a68', '6e9c78'],
    'mist':       ['a9bfbf', 'c4d6d2', 'dde9e3'],
    # wood & structures
    'wood':       ['321e0e', '52331a', '724a26', '915f35', 'ae7a47', 'c8975c'],
    'wood_grey':  ['3b3630', '585148', '776e62', '978c7c', 'b4a996'],            # weathered dock/beam
    'bark_birch': ['3d3f3c', '8c8f88', 'c9ccc3', 'eceee6'],
    'canvas':     ['5f4e38', '836d4e', 'a68a63', 'c6aa7a', 'ddc593', 'eedcb0'],
    'rope':       ['7a6a4c', 'a8956a', 'cbb887'],
    'ruin':       ['2d2f36', '474a52', '62656d', '7d8088', '989ba2', 'b1b4ba'],
    'rubble':     ['3a3c44', '55585f', '70737a'],
    'metal':      ['2e2a28', '4b443f', '6c6259', '8a7f74'],
    'metal_rust': ['5a2e1c', '8a4a28', 'b36a38'],
    # emissive (special night mapping)
    'lantern_glass': ['c7832d', 'f0b24a', 'ffd98a', 'fff3cf'],
    'tent_interior': ['3a3028', '4a3e33', '5a4c40'],  # dark by day, warm glow by night
    'fire':       ['b03a1a', 'e2702a', 'f6a640', 'fde28a'],
    'ember':      ['3a2a22', '5a3a2a'],              # cold ash by day, glowing by night
    'firefly':    ['c8d870'],
    'eyes':       ['e6e0a8'],
    'moonlight':  ['7f94b8', 'a8bbd8', 'd4e0f2'],   # night-only streak/reflection accents
    'shadow':     ['000000'],                        # never drawn directly; see shade table
}

# Night overrides: families whose night look is *designed*, not derived.
NIGHT_OVERRIDES: dict[str, list[str]] = {
    'lantern_glass': ['f0a640', 'ffcc63', 'ffe8a6', 'fff8e0'],
    'tent_interior': ['c87a2e', 'e8a44a', 'ffd27a'],
    'fire':          ['c84a18', 'f08a2c', 'ffc048', 'fff0a0'],
    'ember':         ['9a3a18', 'e07a2c'],
    'firefly':       ['e8ff9c'],
    'eyes':          ['f3eec0'],
    'glowshroom':    ['3fa7b8', '7fe0e6', 'c8fff6'],
    'moonlight':     ['8aa2c8', 'b9cce8', 'eaf2ff'],
    'water':         ['0b1626', '112238', '17304c', '1f3e5e', '2e5578', '5a7fa0', 'a7c4e0'],
    'mist':          ['2a3650', '36456a', '465880'],
    'haze_far':      ['1a2438', '202c44', '283652'],
    'haze_near':     ['141d2e', '1a2538', '212e44'],
    'forest':        ['0d1522', '121c2c', '172436', '1c2b3f', '223349'],
    'dirt':          ['151a26', '1e2534', '2a3244', '363f54', '434d63', '525d72'],
    'worn':          ['1a2a2e', '233740', '2e4650', '3a5560', '48646f'],
}

# ---------------------------------------------------------------------------
# Seasons are lookup tables too. A season table is the day table with
# per-family overrides; its night version is derived from it by the same
# night rule, so every season automatically has a night.
# ---------------------------------------------------------------------------
SEASON_OVERRIDES: dict[str, dict[str, list[str]]] = {
    'spring': {},
    'summer': {
        'grass':  ['1a3626', '285230', '396f3a', '4f9440', '6aae47', '8cc452', 'b0d862'],
        'oak':    ['17331f', '204b28', '2f6833', '3e873c', '55a346', '7abe53', 'a2d563'],
    },
    'autumn': {
        'grass':  ['27392a', '3b5233', '5a6e3c', '7b8a44', '9aa050', 'b7b85c', 'ccc86a'],
        'worn':   ['5a5c34', '76773c', '929246', 'aaa852', 'c0bc62'],
        'forest': ['2a2c22', '3a3a2a', '4c4a32', '5e5a3a', '6e6a44'],
        'oak':    ['3a2416', '6a3a1a', '9a4f1c', 'c4702a', 'dd9238', 'efb14e', 'f8cf72'],
        'birch':  ['3f3a1e', '6e5f22', '9a8426', 'c4a82e', 'e2c646', 'f0dc70'],
        'rowan':  ['4a2a1a', '7a3a1e', 'a8502a', 'cd7038', 'e89a4e'],
        'shrub':  ['2f3a22', '4f5a2a', '7a7a30', 'a08c38', 'c0a548', 'd8c06a'],
        'fern':   ['3a4028', '5a6530', '7a8438', '9aa048', 'b8b860'],
        'reed':   ['6a5a2a', '8a7a36', 'a89a44', 'c4b85a'],
        'lily':   ['4a4a2a', '6a6a34', '8a8a40', 'a8a450'],
        'moss':   ['4a6a2e', '66883a', '88a444', 'a8bc54'],
        'haze_near': ['6a6e5a', '7a8068', '8c9276'],
    },
    'winter': {
        'grass':  ['3f4a44', '55605a', '6f7a6e', '8a9484', 'a3ab98', 'b9bfa8', 'ccd0b8'],
        'worn':   ['4a5048', '606860', '7a8278', '929a90', 'a8b0a4'],
        'forest': ['3f4a48', '4e5b58', '5e6c68', '6e7c76', '7e8c84'],
        'dirt':   ['3b3230', '544843', '6e6058', '887a70', 'a09387', 'b8ab9f'],
        'earth':  ['3e3634', '564d48', '6e645e', '867c74', '9c948c'],
        'mud':    ['3a3634', '4e4a46', '635e58', '78736c'],
        'water':  ['5f7f98', '6f8fa8', '7f9fb5', 'a3c0d0', 'c8dde6', 'e6f2f6', 'f4fafc'],
        'moss':   ['4a5a3e', '627450', '7a8c62', '92a474'],
        'fern':   ['4a4030', '6a5c40', '8a7a52', 'a89866', 'c0b07a'],
        'reed':   ['5a523a', '786e48', '968a56', 'b0a46a'],
        'lily':   ['3a4038', '4f5648', '666e5a', '7a846c'],
        'oak':    ['22302a', '2d3f36', '3b5244', '4a6552', '5c7a62', '6f8f72', '869f86'],
        'birch':  ['2e3a34', '3f4f44', '546652', '6a7e62', '849878', 'a0b090'],
        'shrub':  ['26302a', '384a3a', '4c6048', '627656', '7c9068', '98aa80'],
        'rowan':  ['2c3a2e', '3f5040', '566852', '6c8064', '889a7c'],
        'haze_far': ['8a9aaa', '9cacba', 'aebcc8'],
        'haze_near': ['6f8390', '7f929e', '8fa2ac'],
        'mist':   ['c0ccd6', 'd4dde6', 'e6edf2'],
    },
}

def night_derive(rgb, rank, nranks):
    """Default night mapping: compress value, cool toward slate-blue by mixing
    (never by rotating hue, which drags browns through magenta), keep the top
    rank of each ramp legible with a touch of moonlight."""
    r, g, b = [v / 255 for v in rgb]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    # desaturate partially, then darken
    r, g, b = [lum + (v - lum) * 0.55 for v in (r, g, b)]
    scale = 0.07 + 0.40 * lum / max(lum, 1e-6) if lum > 0 else 0.07
    c = (r * 255 * 0.42 + 12, g * 255 * 0.46 + 18, b * 255 * 0.62 + 34)
    # blue-grey night key, stronger on dark ranks so shadows unify
    key = (20, 30, 56)
    t = 0.36 if rank < nranks // 2 else 0.26
    c = lerp(c, key, t)
    if nranks > 1 and rank >= nranks - 2:
        c = lerp(c, (150, 175, 215), 0.20 if rank == nranks - 1 else 0.08)
    return clamp8(c)

class Palette:
    def __init__(self):
        self.entries: list[tuple[str, int]] = [('transparent', 0)]
        self.day: list[tuple[int, int, int]] = [(0, 0, 0)]
        self.night: list[tuple[int, int, int]] = [(0, 0, 0)]
        self.index: dict[tuple[str, int], int] = {}
        for fam, ramp in FAMILIES.items():
            if fam == 'shadow':
                continue
            n = len(ramp)
            for rank, hx in enumerate(ramp):
                i = len(self.entries)
                self.entries.append((fam, rank))
                self.index[(fam, rank)] = i
                rgb = _hex(hx)
                self.day.append(rgb)
                if fam in NIGHT_OVERRIDES:
                    self.night.append(_hex(NIGHT_OVERRIDES[fam][rank]))
                else:
                    self.night.append(night_derive(rgb, rank, n))
        assert len(self.entries) < 256, len(self.entries)
        # season tables (day + derived night) ---------------------------------
        self.luts: dict[tuple[str, bool], list[tuple[int, int, int]]] = {('spring', False): self.day, ('spring', True): self.night}
        for season, ov in SEASON_OVERRIDES.items():
            if season == 'spring': continue
            dayt, nightt = [(0, 0, 0)], [(0, 0, 0)]
            for (fam, rank) in self.entries[1:]:
                n = len(FAMILIES[fam])
                if fam in ov:
                    rgb = _hex(ov[fam][rank])
                else:
                    rgb = self.day[self.index[(fam, rank)]]
                dayt.append(rgb)
                if fam in NIGHT_OVERRIDES and fam not in ov:
                    nightt.append(_hex(NIGHT_OVERRIDES[fam][rank]))
                elif fam in NIGHT_OVERRIDES:
                    nightt.append(night_derive(rgb, rank, n) if fam not in ('lantern_glass', 'tent_interior', 'fire', 'ember', 'firefly', 'eyes', 'glowshroom', 'moonlight') else _hex(NIGHT_OVERRIDES[fam][rank]))
                else:
                    nightt.append(night_derive(rgb, rank, n))
            self.luts[(season, False)] = dayt
            self.luts[(season, True)] = nightt
        # shade table: index -> same family one rank darker (used for cast shadows)
        self.shade = [0] * len(self.entries)
        for (fam, rank), i in self.index.items():
            self.shade[i] = self.index[(fam, max(0, rank - 1))]
        # double shade for deep shadow
        self.shade2 = [self.shade[self.shade[i]] for i in range(len(self.entries))]

    def lut(self, season='spring', night=False):
        return self.luts[(season, night)]

    def i(self, fam: str, rank: int) -> int:
        n = len(FAMILIES[fam])
        rank = max(0, min(n - 1, rank))
        return self.index[(fam, rank)]

    def ramp(self, fam: str) -> list[int]:
        return [self.index[(fam, r)] for r in range(len(FAMILIES[fam]))]

    def family_of(self, idx: int) -> str:
        return self.entries[idx][0]

    def rank_of(self, idx: int) -> int:
        return self.entries[idx][1]

    def nranks(self, fam):
        return len(FAMILIES[fam])

PAL = Palette()
