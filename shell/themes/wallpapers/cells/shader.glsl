// wallpaper.cells() per pixel; keep the two in step.
uniform float u_reach;
uniform vec4 u_sites[24];
uniform vec2 u_cells;

vec3 wallpaper(vec2 uv) {
    float phase = u_time * TURN;
    // In units of the height, so both axes move alike.
    float aspect = u_size.x / u_size.y;
    vec2 p = vec2(uv.x * aspect, uv.y);
    float reach = 0.25 / u_cells.y;
    float best = 1e9;
    float second = 1e9;
    vec2 near = vec2(0.0);
    vec2 next = vec2(0.0);
    float fill = 0.0;
    for (int i = 0; i < 24; i++) {
        if (float(i) >= u_cells.x) break;
        vec4 s = u_sites[i];
        vec2 site = vec2(s.x * aspect, s.y)
            + reach * vec2(cos(phase + s.z) - cos(s.z), sin(phase + s.z) - sin(s.z));
        float d = dot(p - site, p - site);
        if (d < best) {
            second = best;
            next = near;
            best = d;
            near = site;
            fill = s.w;
        } else if (d < second) {
            second = d;
            next = site;
        }
    }
    // Lead along the bisector of the two nearest sites, a pixel wide.
    float edge = dot((near + next) * 0.5 - p, normalize(next - near)) * u_size.y;
    return compose(uv, fill, 1.0 - smoothstep(0.0, 1.0, edge), u_reach);
}
