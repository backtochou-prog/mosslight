extends CanvasLayer
## Autoload. One small contextual prompt; nearest interactable wins.
var _active: Array = []
@onready var prompt: Label = $Prompt
@onready var message: Label = $Message
var _msg_t := 0.0

func show_prompt(i: Interactable) -> void:
	if not _active.has(i): _active.append(i)
	_refresh()
func hide_prompt(i: Interactable) -> void:
	_active.erase(i); _refresh()
func _refresh() -> void:
	prompt.visible = not _active.is_empty()
	if prompt.visible: prompt.text = ("● " if DisplayServer.is_touchscreen_available() else "E · ") + _active.back().label
func show_message(t: String) -> void:
	message.text = t; message.visible = true; _msg_t = 3.2
func _process(delta: float) -> void:
	if _msg_t > 0.0:
		_msg_t -= delta
		if _msg_t <= 0.0: message.visible = false
