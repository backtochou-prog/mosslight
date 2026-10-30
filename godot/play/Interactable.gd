extends Area2D
## Reusable component: drop on any object. Emits `interacted` when the player is inside and presses interact.
class_name Interactable
signal interacted(who: Node)
@export var label := "Inspect"
@export var text := ""
@export var action := &"inspect"      # future: gather, fish, open, talk, build
var _player_inside := false

func _ready() -> void:
	body_entered.connect(func(b): if b.is_in_group("player"): _player_inside = true; InteractPrompt.show_prompt(self))
	body_exited.connect(func(b): if b.is_in_group("player"): _player_inside = false; InteractPrompt.hide_prompt(self))

func _unhandled_input(event: InputEvent) -> void:
	if _player_inside and event.is_action_pressed("interact"):
		interacted.emit(get_tree().get_first_node_in_group("player"))
		InteractPrompt.show_message(text)
