extends Node
## Thin wrapper for the future save system: one versioned file, survival section only for now.
const PATH := "user://mosslight_save.json"
func save() -> void:
	var f := FileAccess.open(PATH, FileAccess.WRITE); f.store_string(JSON.stringify({"survival": Survival.snapshot()})); f.close()
func load_game() -> bool:
	if not FileAccess.file_exists(PATH): return false
	var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(PATH)); Survival.restore_from(d.survival); return true
