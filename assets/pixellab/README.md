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
