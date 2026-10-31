extends Area2D
## One gatherable world node, instanced from nodes.json. State: full / regrow / depleted.
var def: Dictionary
var left := 0; var state := "full"; var depleted_at := -1.0; var depleted_season := ""; var unique_taken: Array = []
@onready var sprite: Sprite2D = $Sprite2D

func setup(d: Dictionary) -> void:
	def = d; left = d.yields; position = Vector2(d.x, d.y); $CollisionShape2D.shape.radius = d.r; _refresh()

func conditions_met() -> bool:
	var season := String(SeasonState.season); var phase := String(Survival.phase()); var wx := String(WeatherState.kind)
	if def.has("seasons") and def.seasons != "all" and not season in def.seasons.split(","): return false
	if def.get("time", "") == "night" and not Survival.is_night(): return false
	if def.get("time", "") == "deep_night" and phase != "deep_night": return false
	if def.get("time", "") == "day" and not phase in ["dawn", "day", "sunset"]: return false
	if def.has("weather"):
		var ok: PackedStringArray = def.weather.split(","); var rainy := wx in ["light_rain", "heavy_rain"]
		if not (wx in ok or ("rain" in ok and rainy) or ("after_rain" in ok and (WeatherState.recent_rain_hours < 6.0 or rainy))): return false
	return true

func _process(_d: float) -> void:
	if state == "full": return
	if def.respawn_mode == "none": return
	var h := Survival.day * 24.0 + WorldClock.hour(); var elapsed := h - depleted_at
	if def.respawn_mode == "season" and String(SeasonState.season) != depleted_season: _reset()
	elif def.respawn_hours != null and elapsed >= float(def.respawn_hours): _reset()
	elif def.respawn_hours != null and elapsed >= float(def.respawn_hours) * 0.5 and state != "regrow": state = "regrow"; _refresh()
	visible = conditions_met() or not def.kind in ["glowcap", "ghostcap", "nightlily", "moth"]

func _reset() -> void: left = def.yields; state = "full"; depleted_at = -1.0; _refresh()
func _refresh() -> void: sprite.region_rect = Gathering.atlas_rect(def.kind, state)

func gather() -> Dictionary:
	if left <= 0 or not conditions_met(): return {"ok": false, "reason": "Nothing here right now."}
	var tool := ToolBelt.best_for(def.tool)
	if tool == "": return {"ok": false, "reason": "You need the right tool for that."}
	if Inventory.is_full(): return {"ok": false, "reason": "Your pack is full."}
	var r := Survival.perform(StringName(def.activity))         # energy + time, exactly once
	if not r.ok: return r
	var got := []
	var table: Array = def.drops.duplicate()
	if def.has("night_extra") and Survival.is_night(): table.append_array(def.night_extra)
	for e in table:
		if def.has("unique") and e[0] in def.unique and (e[0] in unique_taken or Journal.found.has(e[0])): continue
		var q: int = randi_range(int(e[1]), int(e[2]))
		if int(e[1]) == 0 and q > 0 and randf() > 0.55 * float(r.efficiency): q = 0
		if q > 0:
			var added := Inventory.add(e[0], q)
			if added > 0: got.append([e[0], added]); Journal.record(e[0], def.kind); if def.has("unique") and e[0] in def.unique: unique_taken.append(e[0])
	if ItemDB.tools[tool].durability != null and def.tool != "hand": ToolBelt.wear(tool)
	left -= 1
	if left <= 0: state = "depleted"; depleted_at = Survival.day * 24.0 + WorldClock.hour(); depleted_season = String(SeasonState.season); _refresh()
	return {"ok": true, "got": got}

func save_state() -> Dictionary: return {"id": def.id, "left": left, "state": state, "depleted_at": depleted_at, "depleted_season": depleted_season, "unique_taken": unique_taken}
func load_state(s: Dictionary) -> void: left = s.left; state = s.state; depleted_at = s.depleted_at; depleted_season = s.depleted_season; unique_taken = s.unique_taken; _refresh()
