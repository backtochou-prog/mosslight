extends Node
signal changed
var owned: Dictionary = {}; var active := "hand"
func _ready() -> void:
	for id in ["hand", "knife", "axe", "pickaxe"]: owned[id] = {"id": id, "durability": ItemDB.tools[id].durability}
func can_use(tool_id: String, required: String) -> bool:
	var t: Dictionary = ItemDB.tools.get(tool_id, {}); if t.is_empty(): return false
	return required in t.compat and (owned[tool_id].durability == null or owned[tool_id].durability > 0)
func best_for(required: String) -> String:
	if can_use(active, required): return active
	for id in owned: if can_use(id, required): return id
	return ""
func wear(tool_id: String, n: int = 1) -> void:
	var o: Dictionary = owned[tool_id]
	if o.durability != null: o.durability = maxi(0, int(o.durability) - n); changed.emit()
