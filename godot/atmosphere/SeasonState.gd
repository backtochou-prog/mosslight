extends Node
## Current season. Changing it swaps the indexed scene layer + sprite variants (suffix "_winter") and the keyframe set.
signal season_changed(season: StringName)
@export var season: StringName = &"spring":
	set(v):
		if v != season:
			season = v
			season_changed.emit(v)
const ORDER := [&"spring", &"summer", &"autumn", &"winter"]
func next() -> void: season = ORDER[(ORDER.find(season) + 1) % 4]
func litter_scale() -> float: return {&"spring": 0.6, &"summer": 0.3, &"autumn": 1.8, &"winter": 0.0}[season]
func snow() -> bool: return season == &"winter"
