extends Node
signal changed
@export var size := 24
var slots: Array = []
func _ready() -> void: slots.resize(size)
func count(id: String) -> int:
	var n := 0
	for s in slots: if s and s.id == id: n += int(s.qty)
	return n
func add(id: String, qty: int = 1) -> int:
	var it := ItemDB.get_item(id); if it.is_empty(): return 0
	var left := qty
	for s in slots:
		if s and s.id == id and s.qty < it.stack:
			var n: int = mini(it.stack - s.qty, left); s.qty += n; left -= n
			if left == 0: break
	while left > 0:
		var i := slots.find(null); if i < 0: break
		var n: int = mini(it.stack, left); slots[i] = {"id": id, "qty": n}; left -= n
	changed.emit(); return qty - left
func remove(index: int, qty: int = -1) -> int:
	var s = slots[index]; if s == null: return 0
	var n: int = s.qty if qty < 0 else mini(qty, s.qty); s.qty -= n
	if s.qty <= 0: slots[index] = null
	changed.emit(); return n
func split(index: int) -> bool:
	var s = slots[index]; if s == null or s.qty < 2: return false
	var j := slots.find(null); if j < 0: return false
	var half: int = s.qty / 2; s.qty -= half; slots[j] = {"id": s.id, "qty": half}; changed.emit(); return true
func is_full() -> bool: return slots.all(func(s): return s != null)
