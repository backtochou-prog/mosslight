extends Node
## Game time. 1440 minutes per day. `scale` = game minutes per real second / 60 (240 => a day in 6 real minutes).
signal time_changed(minutes: float)
signal phase_changed(phase: StringName)

@export var minutes: float = 780.0
@export var scale: float = 240.0
@export var paused: bool = false
var _last_phase: StringName = &""

func _process(delta: float) -> void:
	if paused: return
	minutes = fmod(minutes + delta * scale / 60.0, 1440.0)
	time_changed.emit(minutes)
	var p := phase()
	if p != _last_phase:
		_last_phase = p
		phase_changed.emit(p)

func hour() -> float: return minutes / 60.0
func advance(game_minutes: float) -> void: minutes = fmod(minutes + game_minutes + 1440.0, 1440.0)
func set_time(h: float) -> void: minutes = fmod(h * 60.0, 1440.0)

func phase() -> StringName:
	var kf: Dictionary = Atmosphere.keyframes[SeasonState.season]
	var h := hour(); var name: StringName = &"night"
	for k in kf.hours.size():
		if h >= float(kf.hours[k]): name = StringName(kf.names[k])
	return name
