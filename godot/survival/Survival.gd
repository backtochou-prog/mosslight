extends Node
## Energy, exhaustion, activities, sleep, day record, save. Driven by the existing WorldClock autoload.
signal energy_changed(value: float, state: StringName)
signal phase_changed(phase: StringName, previous: StringName)
signal day_changed(day: int)
signal activity_done(id: StringName, night: bool)
signal woke_up(day: int, summary: String)

var cfg: Dictionary
var day := 1
var energy := 100.0
var max_energy := 100.0
var state: StringName = &"energetic"
var _last_phase: StringName = &""
var _last_minutes := 0.0
var _walk_acc := 0.0
var record: Dictionary = {}
var days: Array = []
var sleeping := false
var _cooldown := 0.0

func _ready() -> void:
	cfg = JSON.parse_string(FileAccess.get_file_as_string("res://assets/survival/config.json"))
	max_energy = cfg.energy.max; energy = cfg.energy.start
	_start_record()
	_last_minutes = WorldClock.minutes
	WorldClock.time_changed.connect(_on_time)

# ---- clock extensions -------------------------------------------------------
func schedule(season: StringName = SeasonState.season) -> Dictionary:
	var s: Dictionary = cfg.schedule
	var ref: Array = Atmosphere.keyframes[StringName(s.reference_season)].hours
	var kf: Array = Atmosphere.keyframes[season].hours
	var d_dawn: float = kf[0] - ref[0]; var d_night: float = kf[5] - ref[5]
	return {"dawn_transition": s.dawn_transition + d_dawn, "dawn": s.dawn + d_dawn, "day": s.day + d_dawn,
			"sunset": s.sunset + d_night, "early_night": s.early_night + d_night, "deep_night": s.deep_night + d_night}

func phase(h: float = WorldClock.hour()) -> StringName:
	var sc := schedule()
	if h >= sc.deep_night or h < sc.dawn_transition: return &"deep_night"
	if h < sc.dawn: return &"dawn_transition"
	if h < sc.day: return &"dawn"
	if h < sc.sunset: return &"day"
	if h < sc.early_night: return &"sunset"
	return &"early_night"

func is_night() -> bool: return phase() in [&"early_night", &"deep_night"]
func danger() -> float: return cfg.danger.get(String(phase()), 0.0)

func _on_time(minutes: float) -> void:
	if minutes < _last_minutes - 1.0:
		day += 1; day_changed.emit(day)
	var d := fmod(minutes - _last_minutes + 1440.0, 1440.0)
	record.minutesAwake += d
	if is_night(): record.minutesAfterDark += d
	_last_minutes = minutes
	var p := phase()
	if p != _last_phase:
		var prev := _last_phase; _last_phase = p; phase_changed.emit(p, prev)

func advance(minutes: float) -> void:
	var left := minutes
	while left > 0.0:
		var d := minf(15.0, left); WorldClock.advance(d); _on_time(WorldClock.minutes); left -= d

# ---- energy ------------------------------------------------------------------
func state_for(v: float) -> StringName:
	if v <= 0.0: return &"zero"
	for pair in cfg.energy.states:
		if v >= float(pair[1]): return StringName(pair[0])
	return &"zero"

func _update_state() -> void:
	var s := state_for(energy)
	if s != state: state = s
	energy_changed.emit(energy, state)

func spend(amount: float, reason: String) -> float:
	var a := minf(energy, amount); energy -= a
	record.energySpent += a; _update_state(); return a

func restore(amount: float) -> void: energy = minf(max_energy, energy + amount); _update_state()
func set_energy(v: float) -> void: energy = clampf(v, 0.0, max_energy); _update_state()
func efficiency() -> float: return cfg.energy.efficiency[String(state)]

func can_do(act: Dictionary) -> bool:
	if not act.heavy: return energy > 0.0 or float(act.energy) == 0.0
	if energy <= 0.0: return false
	if state == &"critical" and not cfg.energy.allow_heavy_when_critical: return false
	if state == &"exhausted" and not cfg.energy.allow_heavy_when_exhausted: return false
	return energy >= float(act.energy) * 0.5

func tick_movement(game_minutes: float, moving: bool) -> void:
	if not moving or float(cfg.energy.walk_per_game_hour) == 0.0: return
	_walk_acc += game_minutes / 60.0 * float(cfg.energy.walk_per_game_hour)
	if _walk_acc >= 1.0:
		var n := floorf(_walk_acc); _walk_acc -= n; spend(n, "walking")

# ---- activities (registry from config) ---------------------------------------------
func perform(id: StringName) -> Dictionary:
	var act: Dictionary = cfg.activities.get(String(id), {})
	if act.is_empty(): return {"ok": false, "reason": "unknown"}
	if not can_do(act):
		return {"ok": false, "reason": "You are too exhausted for that. Rest first." if energy <= 0.0 else "You are too tired for heavy work right now."}
	var night := is_night()
	spend(float(act.energy), String(id)); advance(float(act.minutes))
	record.activities[String(id)] = int(record.activities.get(String(id), 0)) + 1; record.count += 1
	if night: record.minutesAfterDark += float(act.minutes)
	activity_done.emit(id, night)
	return {"ok": true, "night": night, "efficiency": efficiency(), "anim": act.anim}

# ---- sleep (reusable for beds / houses) ---------------------------------------------
func try_sleep() -> bool:
	if sleeping or _cooldown > 0.0: return false
	sleeping = true; _cooldown = cfg.sleep.cooldown_seconds
	# the caller fades the screen, then calls apply_sleep(); fade-in; sleeping = false
	return true

func apply_sleep() -> void:
	var slept_hour := WorldClock.hour()
	record.sleptAt = slept_hour; record.returnedBeforeDark = not is_night(); days.append(record)
	var wake: float = schedule().dawn
	var wake_m := wake * 60.0
	if WorldClock.minutes >= wake_m: day += 1; day_changed.emit(day)
	WorldClock.minutes = wake_m; _last_minutes = wake_m
	var full := slept_hour >= float(cfg.sleep.full_restore_before_hour) + 12.0 or slept_hour < float(cfg.sleep.full_restore_before_hour)
	set_energy(max_energy if full else maxf(energy, float(cfg.sleep.short_night_restore)))
	_walk_acc = 0.0
	var summary := summarize(record)
	_start_record()
	woke_up.emit(day, summary)

func _process(delta: float) -> void:
	if _cooldown > 0.0: _cooldown -= delta

# ---- day record / journal ------------------------------------------------------------
func _start_record() -> void:
	record = {"day": day, "season": String(SeasonState.season), "activities": {}, "energySpent": 0.0, "minutesAwake": 0.0, "minutesAfterDark": 0.0, "returnedBeforeDark": null, "sleptAt": null, "count": 0}

func summarize(c: Dictionary) -> String:
	var lines: Array[String] = ["Day %d, %s." % [c.day, c.season]]
	if c.count > 0:
		var parts: Array[String] = []
		for id in c.activities.keys(): parts.append("%d× %s" % [c.activities[id], String(cfg.activities[id].label).to_lower()])
		lines.append(", ".join(parts) + ".")
	else: lines.append("A quiet day of walking and looking.")
	var h := roundi(c.minutesAwake / 60.0)
	if h > 0: lines.append("About %d hour%s outside%s" % [h, "s" if h > 1 else "", (", %.1f of them after dark." % (c.minutesAfterDark / 60.0)) if c.minutesAfterDark >= 30.0 else "."])
	if c.energySpent > 0.0: lines.append("Spent %d energy." % roundi(c.energySpent))
	lines.append("Home before dark." if c.returnedBeforeDark else "Back late, by lantern light.")
	return " ".join(lines)

# ---- save / restore --------------------------------------------------------------------
func snapshot() -> Dictionary:
	return {"version": cfg.version, "day": day, "season": String(SeasonState.season), "minutes": WorldClock.minutes, "energy": energy, "maxEnergy": max_energy, "sleeping": false, "record": record, "days": days}

func restore_from(s: Dictionary) -> void:
	day = s.day; SeasonState.season = StringName(s.season); WorldClock.minutes = s.minutes; _last_minutes = s.minutes
	max_energy = s.maxEnergy; set_energy(s.energy); record = s.get("record", record); days = s.get("days", [])
	sleeping = false; _last_phase = phase()        # no duplicate day / phase events on load
