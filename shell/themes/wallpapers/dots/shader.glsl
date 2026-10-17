// wallpaper.dots() per pixel; keep the two in step. The noise's range over
// the whole image comes from still.py's ranges(), in u_range.
uniform float u_reach;
uniform vec4 u_lat[11];
uniform vec4 u_par[11];

float lattice(int i, float c, float s) {
    int slot = i / 4;
    int k = i - slot * 4;
    return pick(u_lat[slot], k) * c + pick(u_par[slot], k) * s;
}

// One octave: rows doubling, half as many columns.
float octave(vec2 at, int rows, int cols, int offset, float c, float s) {
    int fx; int nx; vec4 wx;
    int fy; int ny; vec4 wy;
    taps(at.x, cols, fx, nx, wx);
    taps(at.y, rows, fy, ny, wy);
    float total = 0.0;
    for (int j = 0; j < 4; j++) {
        if (j >= ny) break;
        float row = 0.0;
        for (int i = 0; i < 4; i++) {
            if (i >= nx) break;
            row += pick(wx, i) * lattice(offset + (fy + j) * cols + fx + i, c, s);
        }
        total += pick(wy, j) * row;
    }
    return total;
}

vec3 wallpaper(vec2 uv) {
    float phase = u_time * TURN;
    float c = cos(phase);
    float s = sin(phase);
    vec2 px = uv * u_size;
    float stepPx = u_size.y / 30.0;
    vec2 centre = (floor(px / stepPx) + 0.5) * stepPx;
    vec2 at = (min(floor(centre), u_size - 1.0) + 0.5) / u_size;
    float raw = octave(at, 2, 2, 0, c, s)
        + 0.5 * octave(at, 4, 2, 4, c, s)
        + 0.25 * octave(at, 8, 4, 12, c, s);
    float value = (raw - rangeAt(0)) / max(rangeAt(1) - rangeAt(0), 1e-6);
    float radius = (value - 0.55) / 0.45 * stepPx * 0.22;
    float line = 0.0;
    if (radius > stepPx * 0.04)
        line = 1.0 - smoothstep(radius - 0.5, radius + 0.5, length(px - centre));
    return compose(uv, 0.0, line, u_reach);
}
