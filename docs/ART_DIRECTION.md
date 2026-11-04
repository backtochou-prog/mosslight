# MOSSlight art direction and asset system

One hand for the whole world. Every environment sprite is generated in code at its final pixel size (never resampled),
from the shared palette in `tools/pixelart/palette.py`, and follows the same rules.

## Rules
- **Scale.** The camper is 22 x 36 px, about two 16 px tiles tall. A tent is crawl-in size (~57 x 50), a fire ring a
  stride across (~34), a seat log sits two (~40), an oak is 52-62 x 64-72, a birch slimmer and taller, a fir 26-30 x 46-52.
- **Light.** From the upper left. Every form: lit plane, mid tone, shaded side, dark foot.
- **Outline.** Selective: the boundary in the material's darkest tone, one step lighter on the lit upper/left edge.
  No black outlines; each material outlines in its own colour.
- **Palette.** Families with 3-7 ranks. Shading moves along a family, never across into another hue. The game adds
  a daylight saturation lift at runtime (`SAT_BOOST`), so source colours stay moderate.
- **Material detail, not noise.** Leaf clumps with lit crescents and shaded rims; wood with grain, nail heads, end
  grain rings; stone in planes with crevices; dressed stone in coursed blocks with mortar. Texture comes from authored
  marks on a jittered grid (ground_art), never per-pixel random pepper.
- **Grounding.** Every object has a cast shadow (`shadow`, live at runtime, follows the sun) and a contact footprint
  (`contact`, baked); plants and rocks get grass leaning over their base (`ground_blend`).
- **Seasons keep identity.** A tree's winter self is the same skeleton with the leaves gone (`tree_art.py`); flowers
  give way to mushrooms and leaf drifts in autumn in the same spots; tall plants go to straw in winter (`winter_dry`).

## Where things live
| Module | Contents |
|---|---|
| `tools/pixelart/ground_art.py` | grass clumps, trodden dirt, camp ground, forest-floor fringe, deep-forest canopy, edge tidying |
| `tools/pixelart/camp_art.py` | camp props, faceted rocks (`faceted`), ferns, grass clumps, flower patches, mushrooms, bushes, rowan, fir, `winter_dry`, `ALIASES` |
| `tools/pixelart/tree_art.py` | grown trees: oak x4, birch x2, willow x2, dead snag, each with a bare winter version |
| `tools/pixelart/world_art.py` | cattails, lily pads, arrowhead, sedge, tufts, glow-caps, hollow log, branches, dock, footbridge, fences, way-sign, the ruin (arched wall with steps down, pillar, low wall, rubble, beam), hanging lantern, rock outcrops, heather, leaf heaps |
| `tools/pixelart/composition.py` | placement rules (forest edge, understorey, pond margin) and `season_sprite` |
| `tools/pixelart/scene_clearing.py` | the valley, composed by hand for every landmark |

`ALIASES` maps the older sprite names the rules ask for onto the new art, so the whole map uses one set.

## The valley's places
- **The camp**: the hand-dressed centre (see the campsite pass).
- **Dense woodland** (west and south): edge oaks and birches over a deep canopy, bushes, ferns and long grass between.
- **Open meadow**: flower patches in the sun, a lone rowan, butterflies by day.
- **Pond and riverside**: dock, cattails and lily pads, a willow on the far bank, a big rock at the water's edge.
- **Sedge marsh** (south-east, below the bridge): mud flats and pools, sedge tussocks, cattails, a willow and a drowned
  silver tree, more fireflies at night, a fence keeping the path off the soft edge.
- **Stony rise** (north-west): rock outcrops pushed up through thin soil, dark firs, heather.
- **The ruin** (north-east): coursed stone, ivy, an arched doorway with steps going down into a cold glow.

## Fast look while working
`python3 tools/preview_camp.py [night|summer|autumn|winter]` renders the valley in ~20 s to `/tmp/camp_*.png`.
Full build: `tools/build_scene.py`, `tools/build_atmosphere.py`, `tools/build_play.py` (in that order).
