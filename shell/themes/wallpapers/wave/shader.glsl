// wallpaper.wave() per pixel; keep the two in step.
uniform float u_reach;
uniform float u_tilt;
uniform float u_offsets[18];

vec3 wallpaper(vec2 uv) {
    float core = max(0.8, u_size.y * 0.0012) / u_size.y;
    float fill = 0.0;
    float line = 0.0;
    for (int i = 0; i < 6; i++) {
        float centre = 0.76 + u_tilt * (uv.x - 0.5)
            + 0.060 * sin(TURN * (0.55 * uv.x + u_time) + u_offsets[i * 3])
            + 0.030 * sin(TURN * (1.35 * uv.x - 2.0 * u_time) + u_offsets[i * 3 + 1])
            + 0.012 * sin(TURN * (2.70 * uv.x + 3.0 * u_time) + u_offsets[i * 3 + 2]);
        float d = uv.y - centre;
        float strength = 0.45 + 0.55 * (1.0 - abs(float(i) / 5.0 - 0.5) * 2.0);
        float c = d / core;
        float h = d / 0.022;
        line += (exp(-c * c) + 0.18 * exp(-h * h)) * strength;
        if (d > 0.0)
            fill += exp(-d / 0.08) * 0.12;
    }
    return compose(uv, clamp(fill, 0.0, 1.0), clamp(line, 0.0, 1.0), u_reach);
}
