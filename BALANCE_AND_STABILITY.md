# Balance, progression and stability: Prompt 16

This covers the browser build only (`preview/play.html` and `preview/*.js`), which is the only build that can be run and tested here. Godot has not been ported since Prompt 9.

The numbers below come from `tools/balance_report.py`, which reads the built data and writes `docs/BALANCE_REPORT.md`, and from the test suites.

## 1. What inspection found (before changes)

| problem | effect |
|---|---|
| tools wore out (axe 40 uses, pickaxe 40, knife 60, rod 30) with **no repair and no replacement** | a hard dead end: no logs means no planks and no building; no knife means no fibre and no cord |
| iron ore and coal came only from deposits that **never respawned** (about 1.1 iron ore and 1.4 coal in a whole game) | the advanced bench (2 iron ingots) and everything after it were practically unreachable |
| scrap metal (every 10 days), wire (finite), glass (rare roll) | the cabin waited about 50 days for glass; the estate about 190 days for bolts |
| **nothing ever changed the weather** outside the dev menu | clay never appeared, which blocked stone foundations, timber walls, tile floors and the garden bed. Rain-only fish and finds, rain sound and weather-driven creature behaviour never happened in normal play |
| `Build.sheltered` was called by the HUD, music and ambience but **did not exist** | "inside" was never detected; home stages were only labels; nothing unlocked |
| the Prompt 15 warm light spill also fed creature perception | night creatures saw the player from farther away than designed |
| crafting with a full pack destroyed the overflow while saying it "stays on the bench" | items were lost |
| walking past a neighbour who was waiting cost trust and affection (`checkIgnored`) | a social penalty for ignoring someone, against the project rule |
| no automatic saving, no load on start, one storage slot, no validation | refreshing or closing the page lost the game; a torn write would lose the save |
| the world pixel pass degraded from about 13 ms to about 70 ms after a few seconds of dusk rain | the engine de-optimised one giant `frame()` function |

## 2. Balance and progression

**Supply (renewable, readable).**
- Deposits respawn every 4 days.
- Iron ore is guaranteed: one per strike.
- Scrap respawns every 3 days with a guaranteed glass shard.
- Wire respawns every 5 days and is also drawn from scrap.
- Reed fibre is 4 cuts every 16 h.
- Clay is 4 digs every 18 h, during and after rain.
- Moss respawns every 36 h, and the big oak every 5 days.

**New recipes, all from existing materials:**
- charcoal (2 logs → coal);
- copper ingot (2 copper ore and 1 coal);
- drawn wire (scrap → 2 wire);
- bolts (scrap → 3, at the furnace).

Stone blocks now cost 3 stone for 2 blocks, nails come 8 per scrap, and metal walls cost 1 scrap and 2 bolts.

**Tools:**
- Every tool can be mended **by hand** from stone, cord and a branch, so a broken tool is never the end.
- Axe, pickaxe and knife have three tiers:
  - Basic or Gathering: 40 or 60 uses, efficiency 1.0 or 1.1.
  - Copper: 90 or 110 uses, efficiency 1.25.
  - Iron: 160 or 180 uses, efficiency 1.45–1.5. Copper comes before iron.
- Efficiency now actually works: a chance of one extra main drop, and better odds on the extra finds. Over 200 swings, the iron axe averaged 1.95 logs per swing against 1.44 for the basic one.

**Home stages: each unlocks something, not just bigger costs.**
| stage | how it is reached | what it opens |
|---|---|---|
| 1 Temporary campsite | start | stage-2 parts |
| 2 Woodland shelter | a closed, roofed room with a door | a full night's rest in your own room at any hour; nothing gets past a closed door; **stage-3 parts open** |
| 3 Established homestead | room of 6+ cells, timber-frame walls or better, a window and a bed | +10 morning energy when you sleep at home; **stage-4 walls, roofs and defences open** |
| 4 Reinforced residence | stone, reinforced or slate home, every cell floored, 4+ fence pieces | +20 max health; Brutes do half damage to stage-4 walls; **metal walls open** |
| 5 Fortified woodland estate | 4+ metal walls, a watch platform, 2+ spikes or barricades | +20 morning energy; night creatures appear on your map |

The Build page shows the current stage ("home: woodland shelter (2/5)"). Each locked part says which stage opens it and what the next stage needs. Reaching a stage gives a toast with its benefit, and autosaves.

**Pace (expected values, one player):**

| stage | wait for the scarcest material | stage reached around |
|---|---|---|
| Basic shelter | 3.3 days (fibre) | day 3 |
| Cabin | 9.8 days (clay) | day 13 |
| Reinforced home | 10.1 days (stone) | day 23 |
| Fortified estate | 14.1 days (scrap) | day 38 |

None of these stages waits on a rare random drop.

**Night, fair rather than random:**
- **Ramp:** the spawn budget ramps over the first nights (day 1 is at 45%, day 2 at 70%, day 3 at 85%; measured 3 → 5 → 6 → 7).
- **Placement:** nothing spawns within 110 px of the player, inside a pool of light or inside a room. Creature perception uses the core light pools only.
- **Knockouts:** you wake at the tent with half health; no items are lost.
- **Rewards:** rare night finds (moondew, nightglass, starshard, moonstone, Brute iron) stay a reason to go out. Essential progression never depends on them.

**Weather (new, `Survival.Weather`):**
- **Plan:** a seeded plan of five blocks per day, by season, with persistence between blocks.
- **Limits:** fog only in the morning; snow only in winter.
- **Rain guarantee:** outside winter it rains at least every third day (the longest dry spell over 120 simulated days was 2 days).
- **Forecast:** the morning journal says what the sky will do.
- **Manual settings:** weather set by hand holds for the rest of that day.
- **Links:** it drives the clay bank, rain-only finds, fishing conditions, rain ambience, creature sight and hearing, snow cover and ripples.

**Neighbours:** passing by is free. A request simply waits; trust and affection are never lowered for ignoring anyone. Conversations are still only started by the player.

## 3. Saving

- **Format:** a checksummed envelope (`{app, v, sum, len, body}`).
- **Writes:** go to a temporary slot first, then the previous save is kept as `.bak`, then the main slot is written.
- **Reads:** fall back from main to `.bak` to `.tmp`. A torn or edited save is caught by the checksum. Old plain (v1) saves migrate.
- **Isolation:** each module restores inside a guard, so one bad section cannot break the rest. A save with no day or time is refused cleanly.
- **Contents:**
  - player position and facing, energy and maximum, health and lantern;
  - pack, tools with tier and wear, buildings with work in progress, home stage history;
  - time, day, season, weather and the weather plan;
  - map exploration, field guide, creature guide, fish book and far waters visited;
  - neighbours' relationships, memories, quests and promises;
  - festivals.
  - Settings and audio volumes are kept separately.
- **Autosave triggers:**
  - every 3 minutes of play;
  - every morning;
  - at festival start and end;
  - on a new home stage;
  - immediately whenever the page is hidden (switching apps on a phone) or closed.
- **Feedback:** a small "saved" slip shows when it happens.
- **Continue:** opening the game carries on from the save with a "Welcome back" note. Pause › New game starts fresh and keeps the old journey aside as a copy. Adding `?new=1` to the address also starts fresh.
- **Not saved:** a craft that is mid-progress (a few real seconds) and any fish currently on the line.

## 4. Performance

All numbers are software-rendered Chromium on this server, not a phone.

| scenario | Prompt 14 | Prompt 15 | now |
|---|---|---|---|
| day frame (play suite) | 18.0 ms | 24 ms | **16.6 ms** |
| night with 12 creatures | 19.6 ms | 28 ms | **17–20 ms** |
| 25 s fast-forwarded rain into night | | about 79 ms (degrading) | **19.9 ms**, steady |

How:
- **Moved the per-pixel world pass** out of `frame()` into a small `shadeWorld()` that takes flat typed arrays. The engine keeps it optimised, and it is now about 6 ms instead of 13–70 ms.
- **Shade only what the camera sees:** the view plus a margin, so distant parts of the clearing are skipped. The water pass skips off-screen water.
- **Precompute wind sway** as separable per-row and per-column waves.
- **Store each pixel with one 32-bit write,** with clamping.
- **Bound everything that grows:** particle pools are capped (fire 160, ripples 120, rain by intensity), and the tap targets are rebuilt every frame.
- **Measure:** a frame-time breakdown per section (`window.FT`) is available for future profiling.

No artwork, animation or effect was removed or reduced.

## 5. Tests

11 suites, 422 checks.

| suite | result |
|---|---|
| play | 37/37 |
| survival | 29/29 |
| gather | 34/34 |
| build | 38/38 |
| night | 38/38 |
| fishing | 45/45 |
| social | 34/34 |
| festival | 32/32 |
| atmosphere (Prompt 15) | 33/33 |
| **integration (new, Prompt 16)** | **38/38** |
| audio render | 64/64 |

The new integration suite covers:
- no dead-end materials, guaranteed late sources, and tools that can always be mended;
- tier order and efficiency, consistent crafting costs, and full-pack overflow;
- home stages, shelter, gating and bonuses;
- the night ramp and fair spawn sites;
- the weather plan, the hand-set hold, and how weather reaches clay, fishing and sound;
- the field guide, and collision for building;
- the no-penalty rule for neighbours;
- a full save round trip, corrupted and torn saves, v1 migration, autosave on waking and on hiding, and carrying on after a reload;
- 25 s of long play, and the night frame budget.

Fixture changes to older suites:
- **Build and night suites:** they now unlock all home stages, because they test the parts rather than progression.
- **Older-save simulations (fishing, social and festival suites):** these now read through `SaveState.read()`, because storage now holds an envelope.
- **Nail count:** the build suite reads the per-craft yield from the data instead of assuming 6.
