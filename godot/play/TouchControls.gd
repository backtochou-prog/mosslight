extends Control
## Floating joystick (left half) + interact button (bottom-right), feeding the same input actions as the keyboard.
@export var radius := 28.0
var _anchor := Vector2.ZERO
var _touch_id := -1

func _ready() -> void:
	visible = DisplayServer.is_touchscreen_available()

func _input(e: InputEvent) -> void:
	if not visible: return
	if e is InputEventScreenTouch:
		if e.pressed and e.position.x < get_viewport_rect().size.x * 0.5 and _touch_id == -1:
			_touch_id = e.index; _anchor = e.position
		elif not e.pressed and e.index == _touch_id:
			_touch_id = -1
			for a in ["move_left", "move_right", "move_up", "move_down"]: Input.action_release(a)
	elif e is InputEventScreenDrag and e.index == _touch_id:
		var v := (e.position - _anchor) / radius
		if v.length() > 1.0: v = v.normalized()
		Input.action_press("move_right", maxf(0.0, v.x)); Input.action_press("move_left", maxf(0.0, -v.x))
		Input.action_press("move_down", maxf(0.0, v.y)); Input.action_press("move_up", maxf(0.0, -v.y))

func _on_interact_button_pressed() -> void:
	Input.action_press("interact"); Input.action_release("interact")
