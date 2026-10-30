# Asset specification and status

Legend — **O**: original, code-authored, in palette, used in the scene.
**O-**: original but visibly needs an artist pass. **P**: placeholder.
**M**: missing (required later, not made).

## Terrain (`assets/tiles/`) — v0.3 material library

| Material | Status | Notes |
|---|---|---|
| lush grass, worn grass, forest ground | O | |
| soft dirt, packed earth, pebbled path | O | three path surfaces with distinct identity |
| mud | O | pond banks are now a 2–3 px band inside the water tile; mud material is for hollows |
| sand | O | |
| natural stone, mossy stone | O | fractured bedrock with a raised edge; moss blankets |
| flagstone paving | O | rectangular slabs with earth joints |
| shallow water, deep water | O- | still; animation/reflection is shader work |
| snow, trampled snow (overlay) | O | drift edges; coverage holes |
| leaf litter (overlay) | O | seasonal density |
| ice rim + cracks (winter pass) | O | pale rim at the bank, second dithered ring, hairline cracks |

Legacy table from v0.1 follows for history.


| Asset | Status | Notes |
|---|---|---|
| grass base ×18 (3 families × 6) | O | plus tile-independent tonal pass in the renderer |
| forest-floor transitions (15×4) | O | soft dithered edge, leaf litter |
| worn-grass transitions (15×4) | O | soft dithered edge |
| dirt transitions (15×4) | O | rim shadow, overhanging blades, pebbles |
| stone/flagstone transitions (15×4) | O | whole-stone clipping at boundaries |
| mud/bank transitions (15×4) | O | 1-vertex band around water |
| water transitions (15×4) + depth pass | O- | still water only; animated ripples and reflections are future shader work |
| flagstone landing at the dock / ruin floor | O- | slabs enlarged and muted in pass 2; paving is the weakest terrain material and would benefit most from hand-drawn slab tiles |
| snow / ice families | M | needed for winter; same tile recipe, new ramps |

## Objects (`assets/objects/`, 111 sprites)

Added in v0.3 (all original, code-authored): saplings (oak, birch), hedges ×2,
tall grass ×3, roots ×2 (ground layer), leaf piles ×2, hollow logs ×2, mossy
boulders ×4, willow ×2, arrowhead ×2, poppy-red and yellow wildflowers;
winter: bare oak ×2, bare birch ×2, and snow-capped variants of pines,
shrubs, boulders, log, stump, tent, dock, ruin walls, rubble, beam, hedge,
dead tree, rowan. Winter willow ×2 added (bare arching crown). Winter ferns (drooped, brown, snow-dusted) and reeds (dead, snow-flecked) now have their own shapes.


| Asset | Status | Notes |
|---|---|---|
| oak ×4, birch ×2, pine ×2, rowan ×2, dead tree | O | rebuilt in pass 2 as leaf clusters with short trunks; still code-authored, an artist can refine leaf edges further |
| shrub ×4 (one berried) | O | |
| fern ×3 | O- | reads as fern at 2×+, soft at 1× |
| flowers ×6 (white, pink, blue) | O | accent-only |
| mushrooms ×2, glow mushrooms ×2 | O | glow kind is luminous at night via palette |
| grass tufts ×3, reeds ×2, lily pads ×4 | O | |
| boulders ×6, small stones ×2 | O | mossy, with base contact |
| fallen log, stump, branches ×2 | O | |
| tent | O | ridge tent, worn; interior glows at night |
| campfire, log seat | O | |
| lantern post, hanging lantern | O | |
| fishing dock | O | |
| ruin back wall, side wall, rubble ×2, beam | O- | side wall redrawn as a low broken wall but still reads as a column at 1×; a larger, more sculpted ruin remains the best next art task |
| mannequin | P | debug scale reference only, not world art |
| player character, NPCs, creatures, fish | M | not in scope for this milestone |

## Distant scenery

| Asset | Status |
|---|---|
| haze canopy rows, water tower, mist dither | O- (procedural, simple; fine as backdrop) |

## Night-only pixels

| Asset | Status |
|---|---|
| fireflies (16), forest-edge eyes (1 pair), moon streak on pond | O |

## Tools / capabilities used and missing

Used: Python 3 + Pillow + numpy (authoring and compositing), Node + Playwright
Chromium (viewer screenshots). No image-generation model, no Aseprite, no
Godot runtime were available in the authoring environment (a Godot 4.3 binary
downloaded fine but executing it was blocked by the session's permission policy).

To reach shipping quality the project needs:

1. **A pixel artist pass in Aseprite** (or equivalent) over the exported PNGs,
   in this order: oak/birch canopies, the ruin, the tent, water edge tiles.
   The palette file and the sprite origins must be kept; the art bible says
   how.
2. **Godot 4.3+** on a machine where it can run, to build the TileSet
   terrain sets from the atlases and validate the palette-swap night shader.
3. Optional: an image model for *concept paintings only* (mood boards for
   golden hour / twilight / winter), never for in-game pixels.

## Atmosphere (v0.4)

| Item | Status | Notes |
|---|---|---|
| time-of-day keyframes ×6 per season | O | graded from the authored tables; blended live |
| weather: clear, light rain, heavy rain, fog, snow, wind | O | particles + table grades + wind sway; all shown in the viewer |
| light pools with flicker, emissive ramps | O | quantised falloff, noon colour mixed back |
| events ×4 | O | lighting/palette/weather/time overrides + baked prop layers (ice holes, stools, lantern ring, string lights, benches, bonfire) |
| long shadows at golden hour | O | live shadow masks (noon / long) blended by sun height |
| summer-specific flowering plants | O- | summer swaps white/blue flowers for yellow/poppy and hedges to the flowering variant; no new species yet |
| icicles on structures | O | under overhangs of tent, dock, ruin walls, beam |
| Godot runtime validation | M | reference port only |

## Player (Prompt 05)

| Item | Status | Notes |
|---|---|---|
| camper sprite 14×24, 3 facings × (2 idle + 4 walk) | **P (temporary original)** | in-palette and in-scale, but a character artist should replace it; origin (7,23), frame layout and foot box 8×4 are the contract |
| gather / fish / build / interact animations | M | planned frame rows, not drawn |
| depth maps, collision mask, interactables | O (data) | regenerated by `tools/build_play.py` from the scene |

## Survival HUD (Prompt 06)

| Item | Status | Notes |
|---|---|---|
| HUD card, sun/moon arc, energy bar | O (canvas-drawn) | no bitmap icons yet; an icon strip for health/hunger/weather is M |
| sleep fade + journal card | O | |
| action animations used by activities | P (temporary player rows) | |
