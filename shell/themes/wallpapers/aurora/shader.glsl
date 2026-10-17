// wallpaper.aurora() per pixel; keep the two in step.
uniform float u_reach;
uniform vec4 u_glow_a[4];
uniform vec4 u_glow_b[4];

vec3 wallpaper(vec2 uv) {
    float phase = u_time * TURN;
    float fill = 0.0;
    float glow = 0.0;
    for (int i = 0; i < 4; i++) {
        vec4 a = u_glow_a[i];
        vec4 b = u_glow_b[i];
        float angle = a.x + 0.45 * (sin(phase + a.y) - sin(a.y));
        float dx = (uv.x - 0.5 - cos(angle) * a.z) / b.x;
        float dy = (uv.y - 0.5 - sin(angle) * a.w) / b.y;
        float light = exp(-(dx * dx + dy * dy));
        // One glow in three carries the accent.
        if (i == 2)
            glow = max(glow, light);
        else
            fill = max(fill, light);
    }
    return compose(uv, fill * 0.8, glow * 0.45, u_reach);
}
