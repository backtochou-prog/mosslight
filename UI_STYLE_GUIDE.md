# MOSSlight UI style guide: the field journal

Every screen in MOSSlight is a page of the camper's own field journal: warm paper bound in dark leather, written in brown ink. The guide describes the one design language the browser build now uses. The shared kit is `preview/ui.js` (`window.UIKit`); a screen that draws outside the kit is a bug.

The Stardew Valley comparison is about quality only. Nothing here borrows its frames, wood textures, colours or layout.

## 1. Principles

1. **One focus per screen.** Each page has one title, one list or grid, and one detail area. Nothing blinks for attention.
2. **Paper over world.** Pages are opaque, and the world never shows through behind text. Small slips (the HUD, prompts, notes, toasts) are paper tags.
3. **Ink, not light.** There is no neon, glow or gradient chrome. Colour comes from ink: sepia for text, rust for selection, moss for good things, gold for rare ones. Red appears only for real danger.
4. **Never colour alone.** Rarity is shown by a pip count plus a word; energy and health by a bar plus a number plus a word ("tired", "hurt"); weather by a glyph; selection by rust corner brackets as well as a tint.
5. **Pixel-crisp.** Everything is drawn on integer coordinates in the game's own pixel grid with the game's own typeface. No system fonts are used.
6. **Quick, calm motion.** Pages settle in about 0.16 s and toasts slide about 30 px. Reduce motion turns every slide, page-turn, sway and pulse off.

## 2. Tokens (`UIKit.C`)

| token | hex | use |
|---|---|---|
| paper | `#ecdfbd` | page fill |
| paper2 | `#e3d3a8` | wells, slots, idle buttons |
| paper3 | `#d8c597` | worn edges, disabled |
| leather / leather2 | `#5a3820` / `#7a4e2c` | binding, primary buttons, inactive ribbon tabs |
| ink / ink2 / faint | `#3a2a1a` / `#5e4a32` / `#8c7656` | text: body, secondary, hints |
| rust | `#8a3a1a` | selection brackets, today, the player marker |
| moss | `#4c6a28` | positive, energy when rested |
| gold | `#9a6a14` | rare, sun |
| water | `#2a6680` | weather, water landmarks |
| danger | `#9a2e16` | health, hostile |

The rarity ink colours (`UIKit.RCOL`) are darkened so they read on paper: common `#7a6c52`, uncommon `#4c6a28`, rare `#2a6680`, very rare `#6e3a7a`, exceptional `#a8601a`, legendary `#a8341c`. Each rarity always has 1 to 6 pips.

The **Strong ink** setting darkens all body text to `#1c120a`.

## 3. Type: Mossbook

Mossbook is a pixel typeface drawn for the game, in `tools/pixelart/font.py` and built by `tools/build_ui.py` into `assets/ui/mossbook*.png/json`. It is a rounded, book-hand face with real descenders.

| face | cell | cap / x-height | use |
|---|---|---|---|
| body (`face:1`) | 9 px, baseline 7 | 7 / 5 | all text, labels, numbers |
| heading (`face:2`) | 18 px, baseline 14 | 14 / 10 | page titles only |
| bold body | double-struck | | the time, discovery titles |

Size rules: there are two sizes and no others. The 9 px body cell is the floor. On phones the whole UI layer is drawn at 1.5x (see section 7), so body text is about 13.5 CSS px on a typical phone.

Modules may keep calling `fillText`. A font string containing `mossbook` (for example `'9px mossbook'`) is routed to the pixel face: 11 px or more gives the heading face, and `bold` gives the double-strike.

## 4. Surfaces and controls

- **Page** (`UIKit.paper`):
  - Construction: a leather binding, a paper grain, a hand-ruled inner border with moss-and-rust corner marks, and a worn lower edge.
  - Title: the heading face with an ink underline.
  - Close box: a top-right box that is always tappable.
  - Spreads: `spread:` draws a two-page book gutter.
- **Tag** (`UIKit.tag`): a small paper slip used for the HUD, the prompt line, notes and toasts.
- **Slot** (`UIKit.slot`): a recessed well. Selection draws rust corner brackets, rarity pips sit beneath the item, and the quantity numeral is in ink.
- **Buttons** (`UIKit.button`):
  - The primary button is leather with cream text; there is one per page.
  - Other buttons are paper2 with an ink outline.
  - Disabled buttons are paper3 with faint text.
- **Bars** (`UIKit.bar`): an ink frame on a tan bed, with ten tick marks so the value can be read without colour. Below the low mark the bar is hatched.
- **Page markers:** tabs are sized from their measured text, not on a fixed pitch.
- **The journal ribbon:**
  - Whenever any book is open, a row of leather bookmarks across the top joins all eight books (Pack, Guide, Craft, Build, Fish, Beasts, Folk, Days).
  - Tap a bookmark, or press Tab / Shift+Tab, to switch books.
- **Glyphs** (`UIKit.glyph`): 5x7 hand-plotted marks, for example sun, moon, rain, snow, fog, wind, heart, leaf, lantern, sneak, shelter, pack, book, map and menu.

## 5. Feedback

| event | feedback |
|---|---|
| picking something up | the item's icon lifts from the spot and arcs into the pack (`UIKit.fly`), plus one short note: "+2 Branch" |
| first find of an item, creature, species | a toast slip, top-right: kicker ("New in the field guide"), name, one line, icon; rare finds get a gold edge, pips and the rare sting |
| a fish never caught before | a discovery page opens with the plate, size, habitat and conditions |
| a recipe unlocked | toast "New recipe" plus the recipe sting |
| crafting | a small card with the recipe icon, a progress bar and a working tick; "Crafted" toast at the end |
| low energy | the bar is hatched and its word changes (rested, tired, worn out, spent, empty); one calm note when you become worn out or spent; a soft vignette only at critical; no flashing |
| damage | the health row shakes for about 0.4 s, a red edge vignette fades out, and the player sprite flinches (hurt frames) |
| a book opens | the page settles from 94% height and the open sound plays; page turns sweep a paper edge |
| save / load | a toast confirms "Saved, Day 3, 14:20", or says plainly why it failed |

Toasts never stack more than three, and repeats within 1.5 s are merged. Notes never stack more than two.

## 6. Layout

- **HUD:** top-left, one slip.
  - It shows the time (bold), the day and season, a sun tick on the day arc, and a weather glyph.
  - Below that sit the energy row (leaf, bar, number, word) and the health row (heart, bar, number, word).
  - Badges for lantern, sneaking and shelter sit beside it.
- **Tools hotbar:** top-right; the slots can be tapped.
- **Prompt line:** bottom centre. With a keyboard it shows an `E` key cap; on touch it shows only the action.
- **Toasts:** top-right under the hotbar. Notes sit at the bottom centre, above the prompt.
- **Books:** centred, kept clear of the top 20 px for the ribbon, and sized from the view so they fit down to a 426x240 UI space.
- **Safe insets:** every edge element is offset by `Camera.safe`.

## 7. Mobile, touch and orientation

- **Target:** Android phones in a mobile browser, landscape.
- **Orientation: landscape only, and here is why.**
  - The clearing is a wide 768x480 world. The camp, the pond and the river all sit across it horizontally, and night play depends on seeing what is coming from the sides.
  - A portrait view would show a sliver about 200 px wide. The HUD, hotbar and thumb controls would then cover most of it.
  - When a phone is held upright, the game pauses and shows a "Turn sideways" page, and resumes when the phone is turned. Nothing is lost.
- **Fitting:** the canvas is letterboxed to fit both axes (it is never cropped). The view width follows the screen shape (480, 640 or 780 x 360), and `viewport-fit=cover` plus safe insets keep controls off notches.
- **Scale:** on touch devices up to 420 px tall, the UI layer is drawn at 1.5x. The setting can be changed in Settings › Display › Interface size (Auto, Small, Medium, Large, Huge).
- **Targets:** every tap target is enlarged to at least 34 UI px. At 1.5x that is about 51 game px, or 44+ CSS px on common phones.
- **Controls:**
  - A thumb stick appears wherever the left thumb lands; pushing it all the way runs.
  - The round act seal sits bottom-right, with an arc of pack, journal and map seals around it.
  - Lamp and strike seals appear only after dark.
  - The menu seal sits top-right.
  - All screens close with their paper close box.
- **Key hints** never appear on touch.

## 8. Accessibility settings (Esc › Settings)

These are saved in `localStorage['mosslight.settings']`:

- Interface size
- Screen shape
- Key hints
- Reduce motion: no slides, page-turns, foliage sway, cloth ripple, pulses or blinking markers
- Strong ink
- Touch controls (Auto, On, Off)
- Weather and festival particles (Full, Reduced)
- Water reflections

Volumes for All sound, Music, Ambience, Effects, Interface and Creatures, plus Mute, are saved separately in `localStorage['mosslight.audio']`.

## 9. Adding a screen

1. Draw inside your module's `draw(g, vw, vh, safe, tab)`. The arguments are in UI space, and `tab` is the daylight UI palette.
2. Use `UIKit.paper` with `close:`, and register every control with `UIKit.button` or `UIKit.hit`.
3. Draw anything anchored to a world position in `drawWorld(g, vw, vh, tab)` instead (it runs at view scale).
4. Announce discoveries with `UIKit.toast` and passing events with `UIKit.note`.
5. Register the screen as a ribbon tab in `play.html` if it is a book.
