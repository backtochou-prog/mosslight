extends ColorRect
## Fade-to-black sleep transition; call `sleep()` from the tent's Interactable. Reusable for beds.
@export var fade_seconds := 1.2
var _t := 0.0; var _phase := ""

func sleep() -> void:
	if not Survival.try_sleep(): return
	_phase = "out"; _t = 0.0; visible = true

func _process(delta: float) -> void:
	if _phase == "": return
	_t += delta
	if _phase == "out":
		color.a = minf(1.0, _t / fade_seconds)
		if color.a >= 1.0: Survival.apply_sleep(); _phase = "hold"; _t = 0.0
	elif _phase == "hold":
		if _t > 0.6: _phase = "in"; _t = 0.0
	elif _phase == "in":
		color.a = 1.0 - minf(1.0, _t / fade_seconds)
		if color.a <= 0.0: _phase = ""; visible = false; Survival.sleeping = false
