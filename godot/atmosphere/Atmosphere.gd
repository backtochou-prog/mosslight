extends Node
## Blends season keyframe tables by hour, applies weather/event grades, writes the palette texture, drives light energy.
var keyframes: Dictionary = {}      # season -> {hours, names, darkness, tables}
var weather_grades: Dictionary = {}
var emissive: PackedStringArray
var entries: Array = []
var palette_image: Image
var palette_tex: ImageTexture
var darkness := 0.0
var light_amount := 0.0
var event: Dictionary = {}

func _ready() -> void:
	for s in ["spring", "summer", "autumn", "winter"]:
		keyframes[StringName(s)] = JSON.parse_string(FileAccess.get_file_as_string("res://assets/atmosphere/%s_keyframes.json" % s))
	weather_grades = JSON.parse_string(FileAccess.get_file_as_string("res://assets/atmosphere/weather_grades.json"))
	var pe: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/atmosphere/palette_entries.json"))
	entries = pe.entries; emissive = PackedStringArray(pe.emissive)
	palette_image = Image.create(256, 1, false, Image.FORMAT_RGB8)
	palette_tex = ImageTexture.create_from_image(palette_image)

func table_at(season: StringName, hour: float) -> Array:
	var kf: Dictionary = keyframes[season]; var hs: Array = kf.hours; var n := hs.size()
	for k in n:
		var h0: float = hs[k]; var h1: float = hs[(k + 1) % n] + (24.0 if k == n - 1 else 0.0)
		var hh := hour + (24.0 if (k == n - 1 and hour < hs[0]) else 0.0)
		if hh >= h0 and hh <= h1:
			var t := (hh - h0) / (h1 - h0); t = t * t * (3.0 - 2.0 * t)
			var a: Array = kf.tables[k]; var b: Array = kf.tables[(k + 1) % n]
			darkness = lerpf(kf.darkness[k], kf.darkness[(k + 1) % n], t)
			var out := []
			for i in a.size(): out.append(Vector3(a[i][0], a[i][1], a[i][2]).lerp(Vector3(b[i][0], b[i][1], b[i][2]), t))
			return out
	darkness = 1.0
	return kf.tables[n - 1]

func grade(tab: Array, kind: StringName, wi: float) -> Array:
	var g: Dictionary = weather_grades[String(kind)]
	var out := []
	for i in tab.size():
		var c: Vector3 = tab[i] if tab[i] is Vector3 else Vector3(tab[i][0], tab[i][1], tab[i][2])
		if wi > 0.0 and not (entries[i].family in emissive):
			var lum := c.dot(Vector3(0.299, 0.587, 0.114))
			var sat := 1.0 - (1.0 - g.sat) * wi; var val := 1.0 - (1.0 - g.val) * wi
			c = (Vector3(lum, lum, lum) + (c - Vector3(lum, lum, lum)) * sat) * val + Vector3.ONE * g.lift * wi
			c = c.lerp(Vector3(g.key[0], g.key[1], g.key[2]), g.t * wi)
		out.append(c)
	return out

func _process(_delta: float) -> void:
	var tab := grade(table_at(SeasonState.season, WorldClock.hour()), WeatherState.kind, WeatherState.intensity)
	for i in tab.size():
		var c: Vector3 = tab[i]
		palette_image.set_pixel(i, 0, Color(c.x / 255.0, c.y / 255.0, c.z / 255.0))
	palette_tex.update(palette_image)
	light_amount = clampf((darkness - 0.08) / 0.6, 0.0, 1.0)

func apply_event(path: String) -> void:
	event = JSON.parse_string(FileAccess.get_file_as_string(path)) if path != "" else {}
	if event.is_empty(): return
	SeasonState.season = StringName(event.season); WorldClock.set_time(event.hour)
	WeatherState.set_weather(StringName(event.weather), event.intensity)
