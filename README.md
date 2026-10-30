# MOSSlight — visual foundation milestone

A 2D cozy-survival game in a reclaimed-by-nature world. This repository holds
the **first milestone: the art direction and one forest clearing** rendered in
two atmospheres. There is no gameplay here on purpose (see the brief).

## What is here

```
ART_BIBLE.md                 visual rules: pixel language, palette, terrain, composition
README.md                    this file
docs/ASSET_SPEC.md           every asset, its status (original / placeholder / missing), tools needed
assets/tiles/                terrain atlases (grass, forest, worn, dirt, stone, mud, water) + JSON
assets/objects/              every object sprite as PNG + objects.json (origins, shadows, tags)
scene/forest_clearing.json   the composition: material vertex map, placements, lights
renders/                     the evidence (see below)
preview/index.html           pixel-perfect viewer with day/night toggle, zoom, gameplay viewport
assets/seasons/              palette lookup tables per season (day + night) for the engine
assets/biomes/               biome resource sets (temperate_forest.json) + planned biomes
scene/terrain_test.json      the terrain test scene composition
tools/pixelart/              the authoring pipeline:
                               palette.py (families, night + season tables), canvas.py,
                               terrain_tiles.py (material library), terrain_render.py (material map, passes),
                               paths.py (path system), composition.py (placement rules),
                               objects.py (sprites), scene_clearing.py, scene_terrain_test.py, render.py
tools/build_scene.py         rebuilds everything: python3 tools/build_scene.py
```

## Exploring the clearing (player, camera, collision, interaction)

```
python3 preview/serve.py          # then open http://localhost:8765/preview/play.html
```
`preview/play.html` is the living-world viewer plus a playable camper: **WASD /
arrows** move (eight directions, normalised diagonals, acceleration), **E /
Enter** interacts when a prompt shows, a smooth camera follows and clamps to
the playable area at integer pixels, zoom 1–3×. "touch controls" enables the
floating joystick (left half) and interact button (bottom-right); they are on
automatically on touch devices and feed the same action vector as the keys.
Time, season, weather and event controls still work, so the player can be
inspected under any condition. The "screen" selector previews phone aspect
ratios (16:9, 19.5:9, 20:10, 4:3) and "safe inset" pushes the HUD and touch
buttons away from screen edges and notches.

Data in `assets/play/`: the temporary original player sheet (`player_idx.png`,
`player.json`), depth maps for y-sorting against the baked scene
(`depth_*.png`, base-y per pixel, foreground = 65535), the collision mask
built from real footprints (`collision.png`), and the interactables list
(`play.json`). Rebuild with `python3 tools/build_play.py`.

Tests: `tests/play_tests.js` drives `play.html` headlessly (movement in eight
directions, diagonal speed, stopping, trunk/pond/tent/ruin collision, the
walkable dock, the path junction, depth sorting behind and in front of trunks
and under framing canopies, camera clamping and smoothness, prompts and
interaction ranges, touch/keyboard parity, day/night/winter visibility, frame
cost). Results: `tests/play_results.json`, screenshots `renders/play_*.png`.

Event prop layers and live shadow masks live in `assets/atmosphere/` (built by
`tools/build_atmosphere.py`); the play build uses them visually, collision
stays the base scene's.

`godot/play/` is the Godot 4 reference port (CharacterBody2D player, Camera2D,
Interactable Area2D component, touch controls). **Unvalidated**: Godot cannot
run in the authoring environment.

## The living world (time, seasons, weather)

```
python3 preview/serve.py          # then open http://localhost:8765/preview/world.html
```
`preview/world.html` runs the world clock live (play/pause, speed 60–3600×,
time slider, `[` `]` step 30 min), with season and weather selectors,
intensity, event overrides and ten numbered test presets. It re-colours the
indexed scene every frame from `assets/atmosphere/` (keyframe tables per
season, weather grades, indexed scene layers, lights). It needs a local
server because browsers block data loading from `file://`.

`godot/atmosphere/` holds the Godot 4 port of the same logic (autoloads
WorldClock, SeasonState, WeatherState, Atmosphere + a palette-swap shader).
It is **unvalidated**: Godot cannot run in the authoring environment.

## How to view

* Open `preview/index.html` in a browser (from this folder, so the relative
  render paths resolve). `N` toggles night; the checkbox shows the 640×360
  gameplay viewport; drag to pan.
* Or open the PNGs directly:
  * `renders/clearing_day_1x.png` / `clearing_day_3x.png`
  * `renders/clearing_night_1x.png` / `clearing_night_3x.png`
  * `renders/view_camp_*_2x.png`, `renders/view_pond_*_2x.png` — gameplay-scale crops
  * `renders/check_*.png` — inspection renders (layering/scale, phone, terrain seams)
  * `renders/clearing_autumn_1x.png`, `clearing_winter_1x.png`, `clearing_winter_night_1x.png` — season tests
  * `renders/terrain_test_spring_3x.png`, `terrain_test_winter_3x.png` — the terrain test scene

## Pipeline in one paragraph

Every asset is authored as **indexed pixel art** (palette indices, not RGB)
by small, hand-designed drawing procedures in `tools/pixelart/objects.py` and
`terrain_tiles.py`. The scene (`scene_clearing.py`) paints a coarse *material
map* and places every object by hand. The renderer composites terrain with a
dual-grid tile family, draws ground decals, cast shadows (one palette step
darker), y-sorted objects, foreground framing, night-only pixels, then
resolves the indices through the **day or night lookup table** and adds
quantised lantern pools. Seasons will be new lookup tables + tile families,
not new scenes.

## Engine plan (Godot 4, GDScript)

No engine project is created yet: Godot could not be executed in the
authoring environment, so an unvalidated project would be a guess. The assets
are already in Godot-friendly form:

* 16-px terrain atlases → one `TileSet` with a `TileSetAtlasSource` per
  material layer; use **Terrain Sets in "match corners" mode** (Godot's
  dual-grid-style corner matching) with the 15 mask tiles + 4 alternates, or
  a 40-line script that reads `material_vertices` from the scene JSON and
  picks tiles exactly as `terrain_render.py` does.
* `objects.json` origins → `Sprite2D.offset`; `shadow` → a child `Sprite2D`
  with a shared ellipse texture and `modulate` darkening, or a `CanvasModulate`
  shadow layer.
* Y-sorting → `Node2D.y_sort_enabled` on the objects layer; the `fg` layer
  above the player.
* Night → a `CanvasModulate` *cannot* reproduce the palette remap. Use a
  palette-swap shader: ship the indexed PNGs (or a 1×N palette texture) and a
  `ShaderMaterial` that looks up day/night tables, with `PointLight2D`
  nodes for the lantern pools (the quantised dither can be a light shader).

## Honest status

Read `docs/ASSET_SPEC.md` for the per-asset list. In short: all art is
original and in-palette, but it is **code-authored pixel art**, not
hand-drawn. It is a coherent, deliberate foundation that a pixel artist should
polish, not a finished product.
