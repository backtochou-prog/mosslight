extends Node
## Weather kind + eased intensity + derived wind. No forecasting: set(kind, target) and it eases in over ~6 s.
signal weather_changed(kind: StringName, intensity: float)
@export var kind: StringName = &"clear"
@export var target: float = 0.0
var intensity := 0.0
var prev_kind: StringName = &"clear"
var prev_intensity := 0.0
var wind := 0.0
const BASE_WIND := {&"clear": 0.08, &"light_rain": 0.35, &"heavy_rain": 0.7, &"fog": 0.05, &"snow": 0.3, &"wind": 1.0}

func set_weather(k: StringName, t: float) -> void:
	if k != kind:
		prev_kind = kind; prev_intensity = intensity; intensity = 0.0
	kind = k; target = t
	weather_changed.emit(kind, target)

func _process(delta: float) -> void:
	intensity += (target - intensity) * minf(1.0, delta * 0.35)
	prev_intensity += (0.0 - prev_intensity) * minf(1.0, delta * 0.5)
	var wt: float = BASE_WIND[kind] * maxf(0.3, target)
	wind += (wt - wind) * minf(1.0, delta * 0.3)

func is_wet() -> bool: return kind in [&"light_rain", &"heavy_rain"]
