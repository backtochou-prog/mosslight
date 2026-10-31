extends Node
var items: Dictionary = {}; var tools: Dictionary = {}; var rarities: Array = []
func _ready() -> void:
	var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/items/items.json"))
	rarities = d.rarities
	for it in d.items: items[it.id] = it
	for t in JSON.parse_string(FileAccess.get_file_as_string("res://assets/items/tools.json")).tools: tools[t.id] = t
func get_item(id: String) -> Dictionary: return items.get(id, {})
func rarity_rank(r: String) -> int: return rarities.find(r)
