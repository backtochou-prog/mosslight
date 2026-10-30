# Godot 4 reference implementation (UNVALIDATED)

These GDScript autoloads and the shader are a direct port of the logic that
runs (and was tested) in `preview/world.html`. Godot could not be executed
in the authoring environment, so this code has **not** been run. Treat it as
a precise spec with the maths already worked out, not as shipped code.

Wiring:
* Autoloads: `WorldClock`, `SeasonState`, `WeatherState`, `Atmosphere`.
* The world is drawn from **indexed** textures (R = palette index) through
  `palette_swap.gdshader`; `Atmosphere` writes a 256×1 palette texture every
  frame from the blended keyframe tables (`assets/atmosphere/*_keyframes.json`).
* Lights: `PointLight2D` per lantern/fire with the quantised falloff texture
  (`light_falloff.png` to be baked from the Bayer-banded curve), energy =
  `Atmosphere.light_amount * flicker`.
* Weather particles: `GPUParticles2D` with 1–2 px quads; counts from
  `WeatherState.intensity`; wind feeds the canopy shader uniform `u_sway`.
* Events (`assets/events/*.json`) override season/hour/weather/grade/lights
  via `Atmosphere.apply_event()`; props are a scene variant.
