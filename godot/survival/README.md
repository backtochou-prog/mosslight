# Godot 4 reference port of the survival clock (UNVALIDATED)

Port of `preview/survival.js` (tested in the browser build). Godot cannot run in the
authoring environment, so this code has not been executed. Numbers come from
`assets/survival/config.json` (written by `tools/build_survival.py`) so both builds balance identically.

Autoloads (order matters): WorldClock → SeasonState → Atmosphere → **Survival** (this folder's `Survival.gd`
which owns Energy, Activities, Sleep, DayRecord, SaveState as inner objects) → SurvivalHud (CanvasLayer).
No second clock: `Survival` listens to `WorldClock.time_changed` and advances time through `WorldClock.advance()`.
