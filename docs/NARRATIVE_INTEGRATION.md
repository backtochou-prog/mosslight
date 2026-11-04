# Narrative integration

Source of truth: `docs/narrative/CHARACTER_BIBLE.md`, `DIALOGUE_LIBRARY.md`, `WORLD_NARRATIVE.md` (unchanged copies of the files provided).
Build: `python3 tools/social_data.py` (runs `tools/narrative.py` to parse the three files, `tools/narrative_map.py` for the rules, then writes `assets/social/cast.json`, `narrative.json` and `narrative_report.json`).
Tests: `tests/narrative_tests.js` (15 checks) plus the existing `social_tests.js`.

## How the writing reaches the game
- **Words are never retyped.** Every spoken line is read out of the markdown. The only change is typography the pixel font cannot draw (curly quotes become straight).
- **150 exchanges in the library: 138 connected, 12 waiting** (below). Each exchange keeps its turns, in order, with the player's lines shown as the player's own.
- **Where each one lives** (`tools/narrative_map.py`, one rule per exchange): *talk* (what a character opens with when you press Talk; fits the hour, weather, season, place and mood), *topic* (listed under "Say something", offered as the player's own words), *meet* (first meeting only), *beat* (story moments, offered as a separate button, always declinable), *gift* (replaces the generic reaction when that item is given).
- **Conditions used:** hour, weather, season, place, bond tier, days since last talk, health/energy, Hush Hounds near, ridge, festival, earlier exchanges (`seen:`), world flags (`flag:`, `world:`), items given (`gave:`). A condition the game cannot evaluate was reduced to the simplest compatible one (for example "after the player has seen X" becomes a seen-flag), never invented.
- **Memory.** Exchanges that speak of a shared past (`tessel.11`, and the like) are gated on a real count of talks or a real memory; the build lint refuses any exchange that claims a past without one. `lull.14` is a dream and is exempt on purpose.
- **Story beats unlock in order** (for example Nera's confession needs the earlier quiet beat and a close bond). Declining ("Not now") plays the library's own choice response, changes nothing, and the beat stays available.
- **Players start every conversation.** Nobody approaches, calls out, or follows. Overheard scenes (below) play only if the player has been standing near, once, and can be dismissed with a tap.

## The six overheard scenes
The six "cross-character" scenes from the library appear as a text caption near the bottom of the screen if the player lingers within ~110 px of both speakers for 3 s while all the speakers have been met. They do not turn to the player, never open a conversation, and each plays once. Routines were extended so the speakers meet (Morrow and Sella at the lantern in the evening; Luma dozing against the roots in fog; Sella leaving a wick on the pond bank after rain; Nera tasting the inflow once close; and the festival scene at the fire).

## The world, opened a little at a time
`WORLD_NARRATIVE.md` pages are written into the Neighbours journal under a character's new **Stories** tab as *Vale notes*:
| Page | Opens when |
|---|---|
| The Listening Turn | Pip tells it (`pip.23`) |
| The Borrowed Shore | Pip tells it (`pip.5`) |
| The Lantern Walk | Nera, Sella or Morrow talk about it |
| The Root Rooms (folklore and place) | Orun, Nera or Morrow speak of the knock / the mark, or the root door is opened |
| The Second Dawn | Luma tells it (`lull.18`) |
| The Empty Bowl | Pip, Orun or Luma talk about the first frost |
| Pondside Camp, The Pond, Lantern Row (places) | the player walks there, after meeting at least one neighbour |

Stories also hold what each friendship has earned from the bible: *Among the neighbours* (from familiarity), *Wants and fears* (from close), and *Kept quiet* (the secret, only once the deep-trust exchange has been shared). Nothing is shown before then. The bible's "Story arc" and "Player relationship" sections are design notes for the writers and are deliberately not shown to players.

## Saves
Notes and heard scenes live in the existing world record; an older save without them loads normally and nothing is duplicated.

## What could not yet be connected to a game feature
| Exchange | Waiting on |
|---|---|
| Nera 20 (disliked perfume) | there is no perfume item |
| Nera 21, Luma 17 (Low Archive) | the Low Archive place does not exist yet |
| Pip 17, Sella 21, Morrow 21 (Weather Station) | the Weather Station does not exist yet |
| Pip 18, Orun 21, Luma 21 (Glass Orchard) | the Glass Orchard does not exist yet |
| Orun 20, Luma 20 (bell) | no bell can be found or made |
| Luma 19 (pear) | no pears in the game |

Other world content with no home yet: the folklore *The House That Keeps Weather* (Weather Station) and *The Bellwether* (no such creature); the places *The Weather Station*, *The Glass Orchard*, *The Low Archive*; the creatures (Mirebacks, Cinder Moths, Glasslings, Night Choir) are not given journal notes (only the Hush Hounds appear in the game); the seasonal customs (spring drain-clearing, winter lights) have no activity of their own beyond the festivals already in the game; the shared-thread clues (the Continuance mark, the torn weather-station page) need the missing places to be discovered in play. When a place or item is added, add its anchor or item id to the exchange's rule in `narrative_map.py` and rerun the build; the report updates itself.

## Older hand-written storylines
The earlier storylines (the thinning, morel, door, birches, beacon, fog) and their memory-bound recall lines were kept; the first-draft names (Ebb, Wick, Burl, Tessel, Lull) are renamed to the library's (Nera, Sella, Orun, Morrow, Luma) wherever the player can read them, and narration of Sella uses "she". Their older greetings were retired in favour of the library's openers.
