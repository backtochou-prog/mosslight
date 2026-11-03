# Atmosphere and audio report: Prompt 15

This report covers the browser build (`preview/play.html` plus `preview/*.js`), which is the only build that was run and tested. Godot can't run in this environment, and **nothing from Prompts 10 to 15 has been ported to Godot**.

## 1. What was inspected first

Before any change, four read-only audits looked at:

- every screen, at desktop and phone size;
- animation;
- audio;
- lighting.

They found these problems:

- **Two unrelated UI styles:** dark glass with system monospace, and flat parchment with Georgia.
- **No game typeface.**
- **Icons dimmed by the night palette.**
- **Rarity shown by colour alone.**
- **Build UI soft-locked on touch.**
- **Most screens keyboard-only.**
- **Portrait orientation broke the layout.**
- **The camp didn't read as a pool of light,** and lamplight turned grass olive.
- **A flat teal night.**
- **Near-silent audio** that never unlocked on touch.
- **Only one volume slider,** and nothing was saved.
- **Missing animations:** no run, blink, hurt or sleep frames, no smoke or embers, no ripples, no settling snow.

The screenshots taken then are kept in `renders/audit/`.

## 2. Sound design: `preview/audio.js` (`window.Sound`)

Everything is synthesised live with WebAudio from oscillators and filtered noise. There are no sample files, and nothing is borrowed from another game.

- **Buses:**
  - Routing: master → music (with a duck for stings), ambient, sfx, ui and creatures.
  - Persistence: every volume and the mute state are saved in `localStorage['mosslight.audio']`.
  - Controls: Settings › Sound has a slider for each bus plus Mute, and the header slider sets master.
- **Unlock:**
  - When: the engine starts on the first key press, mouse click or touch.
  - Visibility: it suspends when the tab is hidden.
- **Ambience:** a mixer of beds whose levels follow what the engine senses every 100 ms (biome, phase, season, weather, distance to water, fire and tent, tree density and shelter):

| layer | follows |
|---|---|
| wind | wind strength; also sets the band centre |
| leaves | season (thin in winter) |
| winter whistle | wind, winter only |
| birds | dawn and day, not in rain or snow, fewer in winter and fog |
| insects and cicadas | season, dusk and night; damped by rain and wind |
| night bed | early and deep night |
| owls | night |
| frogs | spring and summer evenings, near water |
| water lap | distance to water |
| rain | rain intensity; muffled under shelter |
| rain on canvas | rain near the tent |
| thunder | heavy rain |
| fire crackle | distance to any fire |

  Snow, fog and shelter also low-pass the outdoor mix.
- **Effects (35 recipes):**
  - Gathering: wood, chop, stone, pick, plant, rustle, berry, rare find, metal and splash.
  - Fishing: cast, float plop, nibble, bite, reel, catch and lost fish.
  - Making: pickup, craft tap, craft done, build knock, place, remove and eat.
  - Player: hurt, swing, hit, sleep and wake.
  - Doors and pages: door and page.
  - Footsteps on four surfaces (grass, dirt, wood and snow), chosen from the palette family under the player's feet.
  - Each recipe has a cooldown so repeated sounds don't stack, and nearby sounds are panned.
- **UI sounds (12):** open, close, page turn, hover, select, confirm, cancel, error, tab, slider, toast and rare toast. The UI kit plays them for every tap and toast.
- **Creatures:** howl, call, tick, groan, rumble, thud and chime. `Monsters.Audio` is now a front for the engine; the old oscillator cues play only if the engine is missing.
- **Stings:** discovery, rare, recipe, milestone and festival. Each one briefly lowers the music.
- **Music:** composed by me, not taken from anywhere. It is a set of written motifs (melodies, chord progressions and bass patterns) for each mood, played by synthesised piano, pad, soft bass and bell, with rests and silences between phrases.
  - **The 12 moods:**
    - morning, Ionian, 72 bpm
    - day, Ionian, 88 bpm
    - sunset, Aeolian, 66 bpm
    - night, Dorian, 56 bpm, in 3/4
    - danger, Phrygian, 63 bpm
    - shelter, Ionian, 60 bpm, in 3/4
    - fishing, pentatonic, 54 bpm
    - winter, Aeolian, 50 bpm
    - one per festival: Awakening, Lydian; Fireflies, pentatonic; Forgotten, Dorian; Silent Tide, Mixolydian
  - **How a mood is chosen:**
    - danger: a creature is pursuing, stalking or attacking within 140 px;
    - otherwise the active festival's mood;
    - otherwise fishing, while fishing;
    - otherwise shelter, at night under a roof or near the fire or tent;
    - otherwise winter;
    - otherwise the mood for the time of day.
  - **Changes:** moods crossfade and are held for at least 20 s. Danger lets go after 8 s of calm.
  - **Discovery** is a sting rather than a mood.

**Sound tests (`tests/audio_render.js`, 64/64 pass):**

- **Coverage:** it renders offline every mood (16 s), five ambience scenes, two crossfades and a sheet of every effect, writing WAVs to `renders/audio/`.
- **What it checks:**
  - nothing clips (all peaks are under 0.29);
  - nothing is silent;
  - each world state picks the right mood;
  - every pair of moods differs measurably;
  - crossfades have no jumps;
  - all 59 recipes make sound;
  - settings persist;
  - a broken world state never throws.
- **Honest limit:** these checks are measurements only. **No person has listened to the result.** It needs a listening pass on a real phone speaker and headphones.

## 3. Lighting (`play.html` `frame()` and `buildLightMap`)

- **Two-ring lights:**
  - Every fire and lantern keeps its bright core and adds a wide, low, warm spill: 2.2x the radius for fires (about 110 px for the campfire) and 1.7x for lanterns.
  - Both rings are Bayer-banded, so they stay pixel-crisp.
- **Warm ramp:**
  - Lamplight now maps each pixel's day brightness onto one warm ramp: deep umber → ochre → candle → cream.
  - That keeps grass dark and warm instead of olive, and the ramp also lights sprites.
- **Real darkness:**
  - Outside the pools the night falls off by up to 36%, toward blue-black.
  - From 22:30 to 04:30 a deeper grade pulls colours toward (14, 18, 40).
  - The test measures open ground at 01:30 as darker than at 21:00 (36.5 vs 38.9).
- **Moonlight:** on clear nights a cool, low light brings back the shapes of light-coloured surfaces. It is weaker in snow and almost absent in rain or fog.
- **Dawn, sunset and fog:** these come from the existing season keyframes and the Bayer-thresholded ground mist. Screenshots are `renders/p15/sunset.png` and `fog_dawn.png`.
- **Sprites:** the player, resource nodes, the tent cloth and NPCs (via `buildCtx.spriteRGB`) fall into the same darkness and light pools as the scene. Resource nodes used to ignore light pools.
- **UI icons** are always drawn with the daylight palette, so they no longer go murky at night.
- **Measured at the lantern close-up preset (spring 23:00):**
  - the camp spill reads luminance 60, warm (red 67 against blue 61);
  - open ground away from camp reads 33.

## 4. Animation audit

| subject | before | now |
|---|---|---|
| player run | none | R or a full stick: speed x1.55, 12 fps run rows for down, up and side, costs 1 energy per 20 s |
| player blink | none | a 0.13 s blink every 3.7 s while idle, in both breath poses |
| player hurt | red flash only | flinch frames while the player is invulnerable after a hit, plus a HUD shake |
| player sleep | fade only | bedroll frames, breathing at 0.6 fps |
| gather, fish, build | existing rows | unchanged |
| craft | no feedback | job card with a two-frame hammer tap, spark and progress bar |
| tent cloth | static | canvas pixels step along their shade ramp in a slow wave; stronger in wind |
| trees | swayed only above wind 0.12 | always a gentle breeze as a travelling wave, weighted by height above the trunk base |
| grass and flowers | static | standing tufts and flowers sway by 1 px |
| water | ripples and reflection (Prompt 12) | plus rain rings on open water |
| fire | palette-ramp flicker | plus rising smoke that drifts with the wind (lit warm at night) and embers; fewer with reduced particles |
| lanterns | sine flicker | layered breathing, plus an occasional brief gutter dip |
| rain | streaks and splashes | plus rings on water |
| snow | falling flakes | snow settles in drifts on open ground while it falls, then melts slowly afterwards (more slowly in winter) |
| creatures | existing frames | unchanged in this prompt; heavy Brute timing was not changed |
| NPCs | existing frames | emotes moved to the world layer; no new NPC behaviour |

**Reduce motion** stops the following:

- foliage, grass and cloth sway;
- page and toast slides and page turns;
- pulses and shakes;
- the player blink;
- the blinking map marker;
- the hammer tap.

Lights hold steady. The test shows a still scene changing far fewer pixels with reduce motion on than off. Fire, water and weather particles still move, because they carry information.

## 5. Performance (software Chromium on this machine)

The frame-cost tests run with a software renderer on a shared server; they are not phone measurements.

- **Before Prompt 15:** 18.0 ms per day frame, and 19.6 ms per night frame with 12 creatures.
- **First version of the new lighting:** 30 ms and 48 to 61 ms.
- **After optimisation:** about 24 ms by day and about 28 ms at night.
  - Unlit pixels are precomputed per palette index.
  - The breeze waves are separable per row and column.
  - Each pixel is stored with one 32-bit write.
- **Limit:** both are under the 60 ms test limit. The day cost is still about 5 ms above Prompt 14, and it has not been measured on a real Android phone.

## 6. Tests

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
| atmosphere (new; UI kit, typeface, settings, pause, map, ribbon, touch, portrait, sound wiring, player animation, lighting, ambient animation) | 33/33 |
| audio render | 64/64 |
| **total** | **384/384** |

The frame-time checks fail when ten suites run at once on this machine, because they compete for the CPU. Run in batches of three, they pass.

## 7. Known gaps

- **No listening pass and no test on a real Android phone.** Touch was tested with simulated taps in headless Chromium.
- **The adversarial review was started and then stopped at your request,** so no independent check has been made beyond the test suites and my own screenshots.
- **The Mossbook bold** makes H and h look close to I and b, so the screens avoid bold on headings.
- **Smaller limits:**
  - Grid cells in the fish book show no rarity pips (the entry page shows them).
  - The fish book's tab strip crosses the page gutter.
  - The social journal wraps `UIKit.pointer` to read tap positions, which `UIKit.Ptr.tx/ty` now provides, so the wrap could be removed.
- **Phone seals:** on a 640x360 phone the act, pack, journal and map seals sit close together, and their label slips crowd one another (`renders/p15/touch_controls.png`). The arc needs more spacing.
- **Older screenshots:** some per-screen screenshots in `renders/p15/` were taken by the screen builders before the final toast and tap-routing fixes.
- **Godot:** no port of any of this.
