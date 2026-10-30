extends CanvasLayer
## Compact top-left card: time · day · season, sun/moon arc, segmented energy bar. Respects a safe-area margin.
@export var safe_margin := 8
@onready var label: Label = $Card/Label
@onready var bar: TextureProgressBar = $Card/Energy
const COLORS := {&"energetic": Color("8cc452"), &"tired": Color("c8b85a"), &"exhausted": Color("d08a46"), &"critical": Color("c0392b"), &"zero": Color("6a5a4c")}

func _ready() -> void:
	Survival.energy_changed.connect(_on_energy)
	$Card.position = Vector2(safe_margin, safe_margin)

func _process(_d: float) -> void:
	label.text = "%s  ·  day %d  ·  %s" % [_clock_label(), Survival.day, String(SeasonState.season)]
	if Survival.state == &"critical": bar.modulate.a = 0.75 + 0.25 * sin(Time.get_ticks_msec() / 1000.0 * 3.0)

func _clock_label() -> String:
	var h := int(WorldClock.minutes / 60.0); var m := int(fmod(WorldClock.minutes, 60.0)); return "%02d:%02d" % [h, m]

func _on_energy(v: float, state: StringName) -> void:
	bar.value = v / Survival.max_energy * 100.0; bar.tint_progress = COLORS.get(state, COLORS[&"zero"]); bar.modulate.a = 1.0
