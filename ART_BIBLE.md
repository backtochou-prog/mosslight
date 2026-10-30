# MOSSlight — Art Bible (v0.5: harmony pass — warm palette, layered canopies, blue pond)

This document is the contract for every visual asset in MOSSlight. Future
agents and artists must extend the art within these rules or update this
file first. Everything in it was decided by looking at rendered results, not
by theory; the reference render is `renders/clearing_day_1x.png` and its
night twin.

## 1. Intent

MOSSlight is a 2D cozy-survival game seen in a 3/4 top-down view. Nature has
reclaimed the world; the player starts with a worn tent in a forest clearing.
The art must make the player want to stay. The three feelings we design for:

* **Shelter** — the camp sits in a protected pocket (a big tree behind it,
  rocks to one side, open meadow in front). Every home the player builds
  later should feel tucked-in like this.
* **Reclaimed, not ruined** — human remains are soft, mossy, half-eaten by
  plants. No rubble piles of grey noise; ruins are *gardens with walls*.
* **Night is the same place, transformed** — nothing is re-drawn at night;
  the palette is re-interpreted and warm light sources take over.

Reference points are used only for *feel*: the generosity and calm of the
best cozy life-sims, the quiet menace of a forest after dark. No tile, sprite
or map from any existing game is reproduced.

## 2. Pixel language

| Rule | Value | Why |
|---|---|---|
| Tile size | 16 × 16 px | Fine enough for ground detail, small enough that objects span several tiles and break the grid. |
| Character height | ~22 px (debug mannequin) | Tent ≈ 2× character height, oak ≈ 4×. |
| Game viewport | 640 × 360 px, integer-scaled (3× = 1080p, 2× = 720p) | 40 × 22.5 tiles on screen; still legible at 1× on a phone. |
| Rendering | nearest-neighbour only, no sub-pixel movement, no rotation of pixel art | Keeps every pixel crisp. |
| Colour storage | **indexed** — every pixel is a palette index, never a free RGB value | Atmospheres and seasons are lookups; artists cannot drift off-palette. |
| Outline | *selective*: the darkest ramp colour of the object's own family on the outer silhouette only; interior forms are separated by value, never by lines | Terrain has **no outlines**; objects have soft dark edges, never black. |
| Light direction | upper-left sun; highlights on the upper-left of forms; cast shadows to the lower-right, mostly sideways (3/4 view flattens them) | One rule for every asset so nothing looks pasted on. |
| Cast shadows | darken the ground by **one ramp step** (indexed "shade" table), soft edge = 1 px checkerboard dither | Shadows stay in palette and look the same on grass, dirt, stone. |
| Dither | ordered (Bayer 4×4) only, for soft terrain blends, mist and light falloff; never random noise | Random noise is what "AI-slop" terrain looks like. |
| Anti-aliasing | none | — |

## 3. Palette

`tools/pixelart/palette.py` is the single source of truth (186 colours in 50
families). Rules for every ramp:

* 4–7 steps per family. Shadows lean **cool** (blue/teal), highlights lean
  **warm** (yellow). Never a straight lightness ramp.
* Saturation peaks in the mid-tones. The brightest step of any natural
  material stays below pure white; the darkest stays above pure black.
* Each family has a defined **night** version. Most are derived by one rule
  (desaturate, compress to 7–45 % value, mix toward slate-blue `#14203A`,
  the top rank picks up a little moonlight). A few are **designed by hand**:
  water (deeper, more reflective), mist/haze (deep blue), forest floor
  (darkest thing on screen) and the **emissive** families below.
* Emissive families (`lantern_glass`, `tent_interior`, `fire`, `ember`,
  `firefly`, `eyes`, `glowshroom`, `moonlight`) are quiet by day and become
  the brightest values in the frame at night. This is how objects "become
  visible in a different way" without any new art.

Swatch sheet (day | night): `renders/_palette_swatches.png`.

Key day ramps (hex, dark → light):

* grass `1b3826 2a5531 3b733c 539a44 72b64c 96cc58 bde06a` (warm, saturated mids; lit ranks lean yellow)
* forest floor `17302a 213f31 2d5438 3b6a3f 4a7f46`
* worn grass `4b6a38 63893f 7ea249 97b656 b0c865`
* dirt `3a2619 5b3e28 7b5736 9b7349 b88f60 d2ad7c` (warm tan, never grey)
* stone `2b2d38 444854 606473 7f838f 9ea2ac bdc0c6`
* water `173a5a 205386 2b6fa8 4090c4 6ab4d8 a4d8ee def4fb` (a clear blue pond; highlights near white)
* canvas `5f4e38 836d4e a68a63 c6aa7a ddc593 eedcb0`
* lantern glass `c7832d f0b24a ffd98a fff3cf`

Planned atmosphere lookups (not built yet, but the architecture needs nothing
new for them): golden hour (warm key, long shadows two steps dark), blue
twilight (cool key, emissives at half strength), winter (grass → snow
ramps, water → ice ramps, canopies → frosted ramps, warm interiors).

## 4. Terrain system

### 4.1 Material library

Terrain is a **dual-grid material map**: materials live on tile corners and
every drawn tile looks at its four corners, so a coarse map gives rounded,
organic boundaries, and bends, corners, T-junctions and one-tile necks all
join without special cases. One **shared 32-px periodic edge wobble** is used
by every material; a material therefore always covers the material beneath
it exactly.

Each material declares what it sits **on** (`under`). A material is painted
only on top of its own `under` chain, never on unrelated layers. That is what
makes pebbles-in-a-path, moss-on-stone, deep-in-shallow water and snow-over-
anything behave: a soft edge's holes reveal exactly the surface that should
be there.

| id | material | sits on | edge style | identity |
|---|---|---|---|---|
| 0 | lush grass | — | — | 2-px blade pairs, rare clover, three mark-density families, tile-free tonal drifts |
| 1 | worn grass | grass | soft | trodden verge; grass shows through; between grass and dirt, never yellow |
| 2 | forest ground | grass | soft | darker, cooler, a leaf here and there; the floor under canopies |
| 3 | sand | grass | soft | pale warm, fine marks, a soft ripple; the sunny bank of a pond |
| 4 | soft dirt | grass | rim | packed earth path: shadowed rim, blades overhanging from above, lit lower edge, a pebble |
| 5 | packed earth | dirt | soft | greyer, flatter, hairline cracks; a harder, older stretch of path |
| 6 | pebbled path | dirt | soft | dirt with 2–3 muted pebbles per tile, pebbles spilling past the edge |
| 7 | mud | grass | soft | dark, damp, a gleam; grass pokes through; for hollows and puddles (the pond bank is part of the water tile, below) |
| 8 | natural stone | grass | ledge | fractured bedrock: long cracks with a lit line above and a shade below; raised edge (lit north rim, 2-row south face) |
| 9 | mossy stone | stone | ledge | the same rock with moss blankets and a dithered moss rim; moss heavier at the ledge foot |
| 10 | flagstone paving | dirt | clip | rounded rectangular slabs, 1-px earth joints, lit top row, dark lower-right; slabs cut by the edge are dropped; grass reclaims edge joints |
| 11 | shallow water | grass | shore | blue a half-step lighter than deep; the tile carries its own **2–3 px wet bank** (mud with grass through it), then a thin lighter water line, lapping light only on the near bank; crisp 2–5 px highlight dashes |
| 12 | deep water | shallow | soft (3 rings) | dark clear blue, calm, a few glints; depth is a material, not a filter |
| — | snow | overlay | drift | lit crest on the upper-left, cool shadow on the lower-right; `snow` on ground, `snow_path` (trampled, exposed earth) on paths |
| — | leaf litter | overlay | — | drifts of 2–4 leaves on grass/forest/worn, density per tile × season |

Atlases: `assets/tiles/terrain_<material>.png` (15 masks × 4 phases) and
`materials.json` (ids, `under`, edge style). Engine note: in Godot each
material is one TileSetAtlasSource; the `under` chain is the paint order.

### 4.2 Edge styles

* **soft** – two Bayer-dithered rings (three for deep water). For materials
  that blend: verge, forest ground, sand, mud, pebbles, packed earth.
* **rim** – a defined edge for dug/trodden earth: darker rim, darkest where
  grass is above, blades overhanging into the dirt, lighter lower edge.
* **ledge** – raised stone: lit north and west rims, a two-row dark south
  face, moss and grass at the foot, grass creeping onto the north edge.
* **clip** – paving: whole slabs only, earth joints, grass in the edge joints.
* **shore** – water against earth: a 2–3 px wet bank inside the edge, then
  the water line (dark under the far bank, light on the near bank). Banks
  are therefore never a full tile wide.
* **drift** – snow: soft edge plus crest/shadow so snow has thickness.

### 4.3 Paths (`tools/pixelart/paths.py`)

A path is a Catmull-Rom spline with a **width profile**, a surface material
and a verge. Stamping paints the verge (soft, grass through it) then the
surface, both with a gentle wobble. **Aprons** widen every path within two
tiles of a junction so a crossing reads as one worn area. Paths connect to
things by ending *inside* them: a pebbled landing at the dock, a dirt pad
with paving at the ruin door.

Decoration is by rule, not by hand: roots where a tree stands within reach
of the path, stone clusters at sharp bends, tufts where the path is wide.
Restraint: never more than one feature per two tiles of path.

Grass passes: three mark-density families from a low-frequency field, plus
an 8×8-dithered tonal drift capped at 50 % so it reads as sunlight.

Ground decals (on terrain, under shadows): leaf litter under big trees, moss
at tree bases / around stone, pebbles on earth near water.

## 5. Environmental composition

Composition is **rules + hand-placed landmarks**, deterministic by seed
(`tools/pixelart/composition.py`). Landmarks (tent, dock, ruin, the big oak,
the lone rowan) are placed by hand; everything around them comes from rules
that respect an occupancy map (no overlapping solid footprints), keep-out
zones (paths, water, entrances, interactables) and spacing.

| rule | what it does | ecology / composition logic |
|---|---|---|
| forest_edge | three tree bands around a clearing (edge / middle / deep fill) | species shift with compass direction: darker pines and oaks to the north so the eye flows south; birches and rowans at the friendly edge; never on a grid |
| understorey | shrubs, ferns, tall grass, saplings in the gaps between edge trees | the shade line is where the low growth lives |
| pond_margin | reads the shoreline: reeds in the shallows of the far and side banks, tufts and a stone on the near bank, arrowheads at the edge, lily pads in sheltered shallow water | reeds need standing water; lilies avoid the open centre; nothing on the dock approach |
| path_decorate | roots where trees crowd the path, stone clusters at bends, tufts on wide stretches | the path explains itself |
| vegetation_cluster | weighted species in a disc, densest at the centre | flowers in sun, ferns in shade; a cluster, then empty space |
| sheltered_corner | ferns + mushrooms + moss against a big tree or rock | damp, shaded pockets |
| ruin_overgrowth | moss, litter, a sapling at the walls' feet | nature taking the building back |
| foreground_frame | canopies and ferns whose bases sit below the frame | the near layer that makes the view feel entered |

Principles that stay true for every biome:

* **Clearings are carved from forest**, not forest placed on grass.
* **Focal hierarchy**: one primary (camp), one secondary (pond + dock), one
  "what's over there" (ruin), one landmark in the empty space (lone rowan).
* **Breathing room**: keep-outs around every landmark; empty meadow is a
  feature, not a gap to fill.
* **Density caps**: no more than one solid object per 2.3–2.7 tiles in the
  forest bands; understorey spacing 1.6 tiles; one flower cluster per sunny
  pocket.
* **Every object has ground contact**: origin on the ground line, a base
  band, a shadow; roots and leaf piles live on the ground layer.

## 6. Object language

Trees (five silhouettes, all with one trunk/root convention):

* **Oak** 64×84 — broad, seven-lobe canopy, dark underside, root flare, knot.
* **Birch** 36×88 — slender, airy, pale dashed bark, canopy with holes.
* **Pine** 44×96 — five scalloped tiers, blue-green, highlight ridge on the
  upper-left edge of each tier.
* **Rowan** 32×52 — small, round, red berry accents (accent, not spam).
* **Dead tree** 40×70 — grey, bare; silhouette interest near the ruin.

Canopies are **overlapping leaf masses drawn back to front** (v0.5). Each
mass has a mid body, a crisp lit cap on its upper-left, a highlight inside
the cap, a shaded crescent on its lower-right, and a **dark separation rim**
along its lower edge where it sits over the mass behind it; the mass behind
gets a 2-px shade band under the new one. Light comes from above: masses low
in the crown sit one rank deeper in shade. Then leaf-tip `^` marks in the
caps, dark `v` marks in the shade, and a **notched silhouette** so the
outline reads as leaves. Crisp bands only, never dither, never nested
concentric ellipses: the masses must read at 1×.

Proportions: the canopy is the tree. Visible trunk is short — about a
quarter of the sprite height for oaks and birches — and the canopy is
wider than it is tall. Tall exposed trunks under small canopies read as
lollipops and were the biggest "prototype" signal in the first pass.

Variation: oaks have four distinct lobe layouts (broad, tall-crowned,
leaning, wide-and-flat) plus mirroring; never one silhouette repeated.

Vegetation: shrub (3 lobes + berry variant), fern (six tapered fronds, lit
fronds face upper-left, outline one step lighter than other objects so it
does not go spiky), flowers (plus-shaped heads, three species, max 5 heads),
mushrooms (2–3 per cluster; the pale `glowshroom` kind is luminous at night),
grass tufts, reeds with two cattails, lily pads with a notch.

Rock: boulders in three sizes made of two lumps, facet lines, a dark base
band, **moss on the lower-left and top** with a dithered moss rim.

Wood: warm `wood` ramp for living/cut wood; cool `wood_grey` for weathered
structures (dock, beam). Logs show end grain rings, bark cracks, moss on top,
a broken branch stub, mushrooms on the shaded side.

Structures: the **tent** is a ridge tent whose ridge runs toward the camera,
lit left slope / shaded right slope, mid-tone gable with a dark doorway,
rolled flap, sewn patch, hem grime, guy ropes to pegs, ground sheet. The
**dock** is a weathered plank plane with a visible thickness strip, stub
posts with lit tops, a lantern hook, mooring rope, bucket and rod. The
**ruin** is two surviving walls (lit top face, stone courses, broken crest, a
window hole, a lintel with a sagging beam), rubble at the ends, a fallen beam,
ivy and moss, flagstone floor, and a young rowan growing inside.

Light sources: post lantern (camp), hanging lanterns (dock, ruin doorway),
campfire. At night each has a **warm pool** quantised to 5 bands with an
ordered dither (no smooth gradients); the pool mixes the *day* colours of the
ground back in, so lamplight reveals true colour. Fireflies and glow mushrooms
get small cool pools.

## 7. Night (and future atmospheres)

1. Render the scene once as palette indices.
2. Apply the atmosphere lookup (`PAL.day` / `PAL.night` / future tables).
3. Add night-only pixels (fireflies, eyes in the forest edge, moon streak on
   the pond) — a few dozen pixels, placed by hand.
4. Light pools as above.

Night must stay readable: the darkest family (forest floor) still separates
from trunks; the meadow stays a half-step lighter than the forest; the pond
is the darkest open area with the brightest highlight (the moon streak).

Winter will be: a snow terrain family replacing grass/forest/worn ramps, ice
edge tiles on the water layer, frosted canopy ramps for the tree families,
snow-cap overlays on rocks/logs/roofs, warm interior lights, and a day table
with a cold blue key. No renderer changes are needed; one lookup table and
one tile family.

## 7b. Depth and layering

Draw order, bottom to top:

1. **Ground** – terrain materials, then the leaf-litter overlay, then decals
   (moss, pebbles, litter drifts), then the snow overlay.
2. **Ground sprites** – roots, leaf piles, lily pads: flat things the player
   walks over.
3. **Cast shadows** – one palette step darker, dithered rim; drawn for every
   object before any object.
4. **Y-sorted objects** – everything with a footprint, *including the
   player*, sorted by ground-contact y. A tree is one sprite here; because
   its origin is the trunk base, the player is drawn over the canopy when
   standing below the trunk and under it when standing above – walking behind
   trunks and under canopies falls out of the sort.
5. **Foreground** – framing canopies and ferns whose bases are below the
   frame; always above the player.
6. **Night-only pixels and lights.**

For the engine, `objects.json` carries `trunk_top` for every tree: rows
below it are trunk/roots (collision, always opaque); rows above are canopy
(the part the player may pass behind). Distant scenery is a separate layer
with light parallax (about 0.3×) and the hazy palette; parallax stays subtle
so the top-down perspective is never contradicted. Atmospheric colour shift
(haze families) and contact shading (base bands, cast shadows) do the depth
work; no blur, no large-scale parallax.

### The player in the stack

The player is one more y-sorted sprite: origin at the feet (ground contact),
drawn through the same palette table and lit by the same lamp pools as the
world, with a small contact shadow on bare ground only. In the baked-scene
build this is done with a **depth map** (base y of the frontmost sprite per
pixel; foreground = 65535): a player pixel is drawn where the scene's depth
is not lower on screen than the player's feet. Walking behind a trunk, under
a canopy and behind the framing foliage all fall out of that one rule. The
collision footprint is the small ellipse at a trunk's base, never the canopy.

## 7c. Biomes and seasons (data, not code)

A **biome** is a resource set: a material subset, species lists per role
(edge / north / deep / water / understorey / meadow / shore), rule
parameters, and palette overrides. `assets/biomes/temperate_forest.json` is
the first; `planned.json` names the next six with their intended atmosphere.
Each biome must read differently at a glance – marsh is mud, shallow water,
reeds, willows and mist; highland is stone, pines and hard shadows – while
sharing the pixel language above.

A **season** is a lookup table (`assets/seasons/<season>_<day|night>.json`)
plus three knobs: litter density, snow coverage, and a sprite suffix for
objects whose *shape* must change. Identity stays stable: a placement is
"oak_2 at (x, y)" in every season; the renderer resolves its seasonal
appearance at draw time (`season_sprite`). Rules:

* Spring/summer/autumn change **colour only** (canopies, grass, verge,
  reeds, lilies, haze) and litter density.
* Winter changes colour **and shape**: deciduous trees become bare crowns
  with snow on the limbs; everything else gains a snow cap (generic
  `snowcap` pass: snow on every upward-facing run of pixels, a cooler row
  beneath); flowers, lilies, arrowheads and mushrooms are not drawn; water
  maps to ice with a pale rim where it meets the bank and hairline cracks on
  open ice (`ice_pass`); snow covers the ground except **under tree canopies**
  (shelter from trunk positions) and a few wind-scoured patches, and paths
  become trampled snow.
* A winter scene must look designed: bare silhouettes, snow thickness,
  exposed earth on paths, warm interior light – never the spring scene with
  a white overlay.

## 7d. The 24-hour world (time of day as grading)

Lighting is never a rectangle over the picture. Every season's day table is
**graded into six keyframes** — dawn, morning, noon, golden hour, twilight,
night — at season-specific hours (summer days are long: dawn 04:30, night
23:00; winter: dawn 07:30, night 19:00). The live renderer blends the two
nearest keyframes with a smoothstep, so the palette moves continuously and
each family's shadows, mids and highlights move on their own curves:

| keyframe | character | shadows | highlights | value |
|---|---|---|---|---|
| dawn | cool, pink-grey, low contrast; the world waking | indigo key | pale rose | 0.86 |
| morning | clean, slightly cool, fresh | barely touched | cream | 1.00 |
| noon | the authored palette, untouched | — | — | 1.00 |
| golden | warm, intimate; emissives begin to show | plum key | amber | 0.95 |
| twilight | cooling fast; lanterns take over | deep blue | lilac | 0.64 |
| night | the designed night tables (v0.1) | — | moonlit top rank | — |

**Emissive families** (lantern glass, tent interior, fire, embers,
fireflies, eyes, glow mushrooms, moonlight) interpolate between their day
and night colours by the keyframe's *darkness* (0 at noon, 0.12 golden,
0.62 twilight, 1 night). **Light pools** scale with the same darkness, so a
lantern is quiet at noon, noticeable at golden hour and the brightest thing
in the frame at night. Pools are quantised (5 bands, ordered dither), mix
the *noon* colour of the ground back in through the light's tint so lamplight
reveals true colour, and flicker per light kind (fire strongest, lanterns
barely, glow slow, fireflies pulsing). A few convincing sources, never halos
on everything.

Night-only pixels (fireflies, eyes, moon streak) fade in with darkness and
are not drawn in winter (fireflies).

**Shadows are a live layer**, not baked into the scene. Two masks per season
(noon ellipses; evening ellipses stretched 2.1× toward the east) are blended
by sun height: short near noon, long toward golden hour, fading out through
twilight. Shadowed pixels step one palette rank down (the shade table), so
shadows stay in palette on any surface.

## 7e. Weather

Weather is a kind + an intensity that **eases in over about six seconds**
while the previous weather eases out; wind is derived from the kind.

* **clear** – nothing; in spring a faint ground mist at dawn.
* **light / heavy rain** – a cool desaturated grade (darker and bluer for
  heavy), two depths of 1-px drops slanted by wind, splashes on the ground,
  sparkles on water. Never straight grey lines everywhere: drops are short,
  sparse at a distance, longer near.
* **fog** – lifted blacks, lower contrast, and a **drifting two-octave mist
  field** thresholded through a Bayer matrix so it stays crisp; denser low
  in the frame, never over emissives. Landmarks must stay readable.
* **snow** (winter) – a pale grade, slow 1–2 px flakes with sine drift and
  wind push; compatible with the snow ground and snow-capped sprites.
* **wind** – canopy pixels sway by a 1-px horizontal shear that varies with
  row and column (never every tree in unison); in autumn, leaves blow.

Weather grades are table operations (`weather_grades.json`), identical in
the viewer and in the engine spec.

## 7f. Events

An event (`assets/events/*.json`) overrides season, hour, weather, an
extra palette grade, extra lights, effect multipliers (fireflies) and a
`props` list. Props are baked into a per-event scene layer with its own
shadow masks (`scene_event_<name>_idx.png`); the viewer swaps layers when
the event is active. Four examples ship:
winter fishing night (lantern ring on the frozen pond, light snow), autumn
gathering at dusk (string-light pools, wind, leaves), summer pond evening
(bonfire, doubled fireflies), night marsh expedition (fog, cyan glow pools).

## 7g. Harmony rules (v0.5)

* **Warm key, cool shadows.** Every natural ramp's mids are warm and
  saturated; its two darkest ranks lean blue-green. The far forest haze is
  green-grey, not blue-grey, so the backdrop belongs to the same woods.
* **Water is blue, not teal.** The pond must read as water at a glance from
  across the map and be the brightest cool note in the frame.
* **Big readable masses, crisp bands.** Canopies, rocks and canvas are shaded
  in flat bands with one lit cap and one dark rim; detail is a few marks, not
  texture noise.
* **The meadow is calm.** Tufts and pockets, never dither; tiny flowers only
  in the sunniest drifts; lily rafts in sheltered water near the shore.

## 7h. HUD conventions (v0.6)

* One compact card, top-left, inside the safe inset: parchment text
  (`#eedcb0`) on a soft dark card (`rgba(24,30,28,.72)`) with a thin pale rim.
  Monospace at 9 px native; never more than two lines.
* Time, day and season as one line; a tiny sun/moon arc instead of an icon
  set; energy as a ten-segment bar coloured by state (energetic green
  `8cc452`, tired straw `c8b85a`, exhausted amber `d08a46`, critical rust
  `c0392b`). Feedback is soft: a slow pulse and a vignette at critical, never
  flashes, alarms or modal warnings.
* Prompts and messages sit bottom-centre in the same card style; the journal
  card on waking is parchment-dark and fades after a few seconds.
* Reserved: a second row under the bar for health / hunger / status marks.

## 8. What is *not* acceptable

* Flat single-colour tiles; visible tile grids; any 16-px repetition that the
  eye can lock onto.
* Random scatter of flowers/rocks "to fill space". Place by ecology and
  composition, in clusters, with empty space between.
* Objects without shadows or base contact; floating lanterns; trees on a grid.
* Mixed outline styles, black outlines, pure white highlights, neon colours.
* Any asset outside the palette, or a night look made by darkening the day.
