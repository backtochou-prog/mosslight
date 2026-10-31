extends Node
signal discovered(id: String)
var found: Dictionary = {}
func record(id: String, node_kind: String) -> void:
	if found.has(id): found[id].count += 1; return
	found[id] = {"first": {"day": Survival.day, "hour": WorldClock.hour(), "season": String(SeasonState.season), "weather": String(WeatherState.kind), "phase": String(Survival.phase()), "node": node_kind}, "count": 1}
	discovered.emit(id)
func progress(category: String = "") -> Vector2i:
	var n := 0; var t := 0
	for it in ItemDB.items.values():
		if category != "" and it.category != category: continue
		t += 1; if found.has(it.id): n += 1
	return Vector2i(n, t)
