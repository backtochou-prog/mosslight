extends CharacterBody2D
## Eight-direction movement with acceleration, normalised diagonals, slide-along collisions.
@export var speed := 64.0           # px/s (character is 22 px tall; tiles 16 px)
@export var accel := 520.0
@export var decel := 760.0
@export var sprite: AnimatedSprite2D
var facing := &"down"
var flip := false

func _physics_process(delta: float) -> void:
	var axis := Input.get_vector("move_left", "move_right", "move_up", "move_down")   # already normalised
	var target := axis * speed
	var a := accel if axis != Vector2.ZERO else decel
	velocity = velocity.move_toward(target, a * delta)
	move_and_slide()                                        # collision + sliding, never raw position writes
	if axis != Vector2.ZERO:
		if absf(axis.x) >= absf(axis.y) * 0.9 and axis.x != 0.0:
			facing = &"side"; flip = axis.x < 0.0
		else:
			facing = &"up" if axis.y < 0.0 else &"down"
	_animate(axis != Vector2.ZERO)

func _animate(moving: bool) -> void:
	if sprite == null: return
	sprite.flip_h = flip
	var anim := String(facing) + ("_walk" if moving else "_idle")
	if sprite.animation != anim: sprite.play(anim)
