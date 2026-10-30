# Godot 4 reference port of the exploration layer (UNVALIDATED)

Direct port of the logic tested in `preview/play.html` and `tests/play_tests.js`.
Godot cannot run in the authoring environment, so this has not been executed.

Scene layout (one `World.tscn`):
```
World (Node2D)
├─ Ground (Sprite2D: indexed scene texture, palette_swap material)   z=0
├─ GroundDecor (Node2D)  roots, leaf piles, lily pads                 z=0
├─ YSort (Node2D, y_sort_enabled = true)
│   ├─ Props…  (each: Sprite2D offset = -origin, StaticBody2D footprint from objects.json)
│   └─ Player (CharacterBody2D)  Player.gd + AnimatedSprite2D + Camera2D (PlayerCamera.gd)
├─ Foreground (Node2D)  framing canopies, z above the player
└─ UI (CanvasLayer)  InteractPrompt.gd, TouchControls.gd
```
* Trees are one sprite each; because the sprite origin is the trunk base, y-sort gives
  "behind the trunk / under the canopy" for free. `objects.json.trunk_top` says where
  the solid trunk starts; the collision shape is the small ellipse at the base only.
* Collision shapes: trees = ellipse at base (rx ≈ w/9, ry 3); rocks/logs = shadow
  ellipse × 0.85; tent/ruin = rectangles (doorway open); dock = none (walkable) with
  water collision cut out under the deck; water = polygon from the material map, eroded 2 px.
* Input actions: `move_left/right/up/down`, `interact`. Keyboard and the on-screen
  joystick both write to these via `Input.action_press` strengths.
