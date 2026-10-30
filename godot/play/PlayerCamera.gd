extends Camera2D
## Smooth follow with a dead zone, clamped to the playable rect, snapped to whole pixels.
@export var smooth := 8.0
@export var deadzone := 0.25
@export var playable := Rect2(32, 48, 704, 400)
@export var margin := 32.0
var _pos := Vector2.ZERO

func _ready() -> void:
	position_smoothing_enabled = false     # we smooth ourselves to keep integer snapping
	_pos = get_parent().global_position

func _process(delta: float) -> void:
	var view := get_viewport_rect().size / zoom
	var target: Vector2 = get_parent().global_position + Vector2(0, -10)
	var mn := playable.position - Vector2(margin, margin) + view / 2.0
	var mx := playable.end + Vector2(margin, margin) - view / 2.0
	target = target.clamp(mn, mx)
	var k := 1.0 - exp(-smooth * delta)
	if absf(target.x - _pos.x) > deadzone: _pos.x += (target.x - _pos.x) * k
	if absf(target.y - _pos.y) > deadzone: _pos.y += (target.y - _pos.y) * k
	global_position = _pos.round()
