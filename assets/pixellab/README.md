# PixelLab art (visual pilot pack)

Generated with PixelLab's official MCP server (`https://api.pixellab.ai/mcp`) by `tools/pixellab/pilot.py`, through the
small client in `tools/pixellab/mcp.py` (the API key is read from `~/.config/mosslight/pixellab.env`, never stored here).

- **Every request** is recorded in `pilot.json`: tool, description, size, seed, palette families, style anchor, job id, cost.
- **Every candidate** is kept as a source file: `src/<asset>/cand_NN.png` (transparent PNG, native size, no resampling).
  Tilesets keep their sheet, metadata (corner layout, bounding boxes) and the server response: `src/ts_*/`.
- **Palette.** Each asset was generated on the game's own colours for its palette families, so the art maps exactly
  onto palette indices: night lighting, seasons (autumn leaves, winter) and weather keep working.
- **Style anchor.** Oak candidate 6 is the style reference (outline, detail, shading) for every later object.
- **2D only.** Objects are drawn front-facing and from slightly above, never at a corner angle (the first tent, crate,
  bench and woodpile were angled and were regenerated as `*2d`).
- **Calm.** Terrain uses the calm sets (`*3`: basic shading, low detail); the first, detailed sets read as pixel noise.

## Picks (what the game uses)
The art-directed choices live in `tools/pixelart/pl_pilot.py` (`PICKS`) and `tools/pixelart/pl_terrain.py` (`SETS`).
Sprites replace library entries by name, so placement, collision, depth and save data are unchanged. Origins are the
ground contact point (trees: the trunk's foot; props: their middle).

| Game name | Source |
|---|---|
| oak_0..3 | oak 6, 1, 8, 5 |
| pine_0/1 (via pine_new0/1) | pine 6, 11 |
| rock_xl, rock_l0, rock_l1, rock_m0, rock_m1, rock_s0..2 | rocks 2, 12, 17; rocks_small 13, 28, 18, 43, 58 |
| bush_a/b/berry/c (shrub_*) | bush 0, 15, 11, 20 |
| fern_a..c, tall_a..c, tuft_0..2 | fern 5, 12, 22; tallgrass 0, 8, 15; tuft 3, 11, 23 |
| patch_daisy/daisy_s/blue/butter/pink/bells | flowers_s 0, 32, 43, 3, 17, 25 |
| shrooms_brown/red/tan | mushrooms_s 15, 11, 57 |
| hollowlog_0, log_moss, log_cut | log 15, 0, 8 |
| tent, supply_crate, log_seat, log_seat_b, woodpile | tent2d 0, crate2d 36, bench2d 9, 31, woodpile2d 0 |
| campfire (+ embers, unlit derived), lantern_post, chop_block | campfire 10, lantern 21, chopblock 13 |
| terrain | ts_grass_dirt3, ts_grass_forest3, ts_water_grass3 (all chained on one grass tile) |

Not yet regenerated (still the earlier drawn art): birches, willows, rowans, the snag, cattails, lily pads, the dock,
the footbridge, fences, signs, the ruin, the highland outcrops, winter (bare) trees.

## Visual refinement 01: terrain noise, grass and the protagonist

**Terrain.**
- The ground uses the calm `*3` tilesets (basic shading, low detail).
- Grass marks are thinned: two in three lone marks go back to the base green. Marks at a path or bank edge stay.
- The dark/light hatching in the shade-grass set is resolved by a 5x5 majority.
- Deeper-grass patches are no longer tile-shaped. They are cut at pixel resolution from a smooth field (the painted
  patches plus a gentle wobble), so their edges are organic and clean.
- Ground detail (pebbles at path edges, tufts and clover at tree and rock feet, a few tiny-flower clusters) is
  placed in clusters. Quiet zones are left around the camp ground and the dock.

**Protagonist** (`src/hero/`, downloaded by `tools/pixellab/hero.py`, built by `tools/pixelart/pl_hero.py`).
- Made with `create_character` from the approved `hero_south` design: 32x40, 4 directions, low top-down view.
  It keeps the auburn hair, green vest, white shirt, blue scarf and grey trousers.
- Animations:

  | Clip | Source | Directions | Frames used |
  |---|---|---|---|
  | breathing-idle | template | 4 | 4 |
  | walking | template | 4 | 6 |
  | running-6-frames | template | S, N, E | 6 |
  | picking-up (gather) | template | 4 | south 0, 1, 3, 4 (frame 2 came out mangled) |
  | taking-punch (hurt) | template | S, N, E | gentle recoil frames only |
  | fishing | custom v3 | E | rod held out |
  | hammering (build) | custom v3 | S | 4 |

- Every frame is mapped onto the game palette (hero families). The rotations map exactly; the animated frames drift
  by at most about 25 RGB.
- Blink frames close the eyes on every idle frame. The sleeping frame is the front pose laid down in a green
  bedroll.
- Sheet layout:
  - Cells are 48x40, so the cast rod fits.
  - Origin (24, 36) is at the feet; the foot box is 8x4.
  - Contacts are detected from the widest stride.
  - Frame rates: walk 10 fps, run 14 fps, idle 2.2 fps.
  - `rod_tip` is exported, so the fishing line leaves from the drawn rod.
