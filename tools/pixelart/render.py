"""Scene renderer: terrain -> ground decals -> cast shadows -> y-sorted objects
-> foreground -> night overlay -> atmosphere lookup + lantern lighting."""
from __future__ import annotations
import math, random, json
import numpy as np
from PIL import Image
from .canvas import Canvas
from .palette import PAL
from .terrain_tiles import T, TerrainTiles, MATERIALS
from .terrain_render import MaterialMap, render_terrain, render_snow, water_depth_pass, meadow_tone_pass, litter_pass, ice_pass
from .objects import Sprite

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0

class Placement:
    __slots__ = ('sprite', 'x', 'y', 'flip', 'layer', 'night_only')
    def __init__(self, sprite: Sprite, x, y, flip=False, layer='ysort', night_only=False):
        self.sprite, self.x, self.y, self.flip, self.layer, self.night_only = sprite, int(x), int(y), flip, layer, night_only

class Light:
    def __init__(self, x, y, radius, color=(1.0, 0.86, 0.62), intensity=1.0):
        self.x, self.y, self.radius, self.color, self.intensity = x, y, radius, color, intensity

class Scene:
    def __init__(self, w_tiles, h_tiles):
        self.w, self.h = w_tiles, h_tiles
        self.W, self.H = w_tiles * T, h_tiles * T
        self.mm = MaterialMap(w_tiles, h_tiles)
        self.placements: list[Placement] = []
        self.lights: list[Light] = []
        self.decals = []            # callables(canvas, rng) applied on the terrain
        self.night_pixels = []      # (x, y, idx) drawn only at night (fireflies, eyes, moon streak)
        self.playable = (0, 0, self.W, self.H)

    def add(self, sprite, x, y, flip=False, layer='ysort', night_only=False):
        p = Placement(sprite, x, y, flip, layer, night_only)
        self.placements.append(p)
        return p

    # -- passes -------------------------------------------------------------
    def draw_shadow(self, c: Canvas, p: Placement):
        s = self.resolve(p.sprite)
        if s is None or not s.shadow: return
        rx, ry, dx, dy = s.shadow
        cx, cy = p.x + dx, p.y + dy
        m = c.ellipse_mask(cx, cy, rx, ry)
        if s.soft_shadow:
            outer = c.ellipse_mask(cx, cy, rx + 2, ry + 1) & ~m
            ys, xs = np.nonzero(outer)
            keep = ((xs + ys) % 2 == 0)
            soft = np.zeros_like(m); soft[ys[keep], xs[keep]] = True
            c.shade_mask(soft)
        c.shade_mask(m)

    season = 'spring'
    lib = None

    def resolve(self, sprite):
        """Stable identity, seasonal appearance (see composition.season_sprite)."""
        if self.season == 'spring' or self.lib is None: return sprite
        from .composition import season_sprite
        return season_sprite(self.lib, sprite.name, self.season)

    def draw_sprite(self, c: Canvas, p: Placement):
        s = self.resolve(p.sprite)
        if s is None: return
        ox = (s.w - 1 - s.ox) if p.flip else s.ox
        c.blit(s.c, p.x - ox, p.y - s.oy, flip=p.flip)

    shadows_baked = True
    extra_placements = []

    def shadow_mask(self, stretch=1.0, dx=0, season='spring'):
        """Cast-shadow coverage (0 none, 1 soft rim, 2 full) for every object,
        with ellipses stretched horizontally (long evening shadows) and shifted."""
        self.season = season
        m = Canvas(self.W, self.H)
        for p in [p for p in self.placements + self.extra_placements if p.layer in ('ysort', 'fg')]:
            s = self.resolve(p.sprite)
            if s is None or not s.shadow: continue
            rx, ry, sdx, sdy = s.shadow
            cx, cy = p.x + sdx * stretch + dx * (rx / 14.0), p.y + sdy
            full = m.ellipse_mask(cx, cy, rx * stretch, ry)
            if s.soft_shadow:
                outer = m.ellipse_mask(cx, cy, rx * stretch + 2, ry + 1) & ~full
                ys, xs = np.nonzero(outer); keep = ((xs + ys) % 2 == 0); m.a[ys[keep], xs[keep]] = 1
            m.a[full] = 2
        return m

    def render_indexed(self, tiles: TerrainTiles, night=False, season='spring', debug_extra=None) -> Canvas:
        self.season = season
        c = render_terrain(self.mm, tiles)
        water_depth_pass(c)
        if season == 'winter': ice_pass(c)
        meadow_tone_pass(c)
        litter_pass(c, self.mm, season)
        rng = random.Random(77)
        for d in self.decals:
            d(c, rng)
        if self.mm.snow.any():
            render_snow(c, self.mm, tiles)
        allp = self.placements + self.extra_placements
        ground = [p for p in allp if p.layer == 'ground' and (night or not p.night_only)]
        ysort = [p for p in allp if p.layer == 'ysort' and (night or not p.night_only)]
        fg = [p for p in allp if p.layer == 'fg' and (night or not p.night_only)]
        if debug_extra: ysort = ysort + debug_extra
        for p in ground: self.draw_sprite(c, p)
        if self.shadows_baked:
            for p in ysort + fg: self.draw_shadow(c, p)
        for p in sorted(ysort, key=lambda p: (p.y, p.x)): self.draw_sprite(c, p)
        for p in sorted(fg, key=lambda p: (p.y, p.x)): self.draw_sprite(c, p)
        if night:
            for (x, y, idx) in self.night_pixels: c.put(x, y, idx)
        return c

    def to_rgb(self, c: Canvas, night: bool, season='spring') -> np.ndarray:
        lut = np.array(PAL.lut(season, night), dtype=np.float32)
        rgb = lut[c.a]
        if night:
            day = np.array(PAL.lut(season, False), dtype=np.float32)[c.a]
            H, W = c.a.shape
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            wmax = np.zeros((H, W), dtype=np.float32)
            tint = np.zeros((H, W, 3), dtype=np.float32)
            for L in self.lights:
                d = np.hypot(xx - L.x, (yy - L.y) * 1.25) / L.radius      # slightly flattened pool
                w = np.clip(1.0 - d, 0, 1) ** 1.6 * L.intensity
                # pixel-art banding: quantise to 5 steps with an ordered dither
                bay = np.tile(BAYER4, (H // 4 + 1, W // 4 + 1))[:H, :W]
                w = np.floor(w * 5 + bay * 0.9) / 5
                w = np.clip(w, 0, 1)
                sel = w > wmax
                wmax = np.where(sel, w, wmax)
                col = np.array(L.color, dtype=np.float32)
                tint[sel] = col
            lit = day * tint * 1.08 + 18 * wmax[..., None]
            rgb = rgb * (1 - wmax[..., None]) + lit * wmax[..., None]
        return np.clip(rgb, 0, 255).astype(np.uint8)

    def render(self, tiles, night=False, season='spring', debug_extra=None):
        c = self.render_indexed(tiles, night, season, debug_extra)
        return c, self.to_rgb(c, night, season)

    def export_json(self, path):
        data = {
            'tile_size': T, 'size_tiles': [self.w, self.h], 'playable_px': self.playable,
            'materials': [m.name for m in MATERIALS],
            'material_vertices': self.mm.m.tolist(),
            'snow_vertices': self.mm.snow.tolist(),
            'litter_tiles': [[round(float(v), 2) for v in row] for row in self.mm.litter],
            'placements': [{'sprite': p.sprite.name, 'x': p.x, 'y': p.y, 'flip': p.flip, 'layer': p.layer, 'night_only': p.night_only}
                           for p in self.placements],
            'lights': [{'x': L.x, 'y': L.y, 'radius': L.radius, 'color': L.color, 'intensity': L.intensity} for L in self.lights],
        }
        with open(path, 'w') as f:
            json.dump(data, f)

def save_rgb(rgb, path, scale=1):
    img = Image.fromarray(rgb, 'RGB')
    if scale != 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    img.save(path)
    return img
