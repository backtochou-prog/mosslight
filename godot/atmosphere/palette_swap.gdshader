shader_type canvas_item;
// Indexed scene: TEXTURE.r * 255 = palette index. u_palette = 256x1 RGB written by Atmosphere every frame.
// u_day_palette = noon table, used by lights (lamplight reveals true colour). u_sway = wind strength for canopy indices.
uniform sampler2D u_palette : filter_nearest;
uniform sampler2D u_day_palette : filter_nearest;
uniform sampler2D u_class : filter_nearest;   // 256x1: r=1 canopy, g=1 water, b=1 emissive
uniform float u_sway = 0.0;
uniform float u_time = 0.0;
void fragment() {
	vec2 uv = UV;
	float idx = texture(TEXTURE, uv).r;
	vec3 cls = texture(u_class, vec2(idx, 0.5)).rgb;
	if (u_sway > 0.12 && cls.r > 0.5) {
		float o = round((sin(u_time * 1.7) * 0.5 + sin(u_time * 2.3 + uv.y * 43.0 + uv.x * 10.0)) * u_sway * 1.2);
		vec2 uv2 = uv - vec2(o, 0.0) * TEXTURE_PIXEL_SIZE;
		float idx2 = texture(TEXTURE, uv2).r;
		if (texture(u_class, vec2(idx2, 0.5)).r > 0.5) idx = idx2;
	}
	COLOR = vec4(texture(u_palette, vec2(idx, 0.5)).rgb, idx > 0.0 ? 1.0 : 0.0);
}
