// wallpaper.ridges() per pixel; keep the two in step. Each ridge's range
// along x comes from still.py's ranges(), in u_range, low then high.
uniform float u_reach;
uniform vec4 u_rl[81];
uniform vec4 u_rp[81];

float lattice(int i, float c, float s) {
    int slot = i / 4;
    int k = i - slot * 4;
    return pick(u_rl[slot], k) * c + pick(u_rp[slot], k) * s;
}

// One ridge's height along x: its row of each octave, interpolated in x.
float ridge(float u, int r, float c, float s) {
    float total = 0.0;
    float amplitude = 1.0;
    int offset = 0;
    for (int k = 0; k < 4; k++) {
        int cols = 2;
        if (k == 1) cols = 3;
        if (k == 2) cols = 6;
        if (k == 3) cols = 12;
        int f; int n; vec4 w;
        taps(u, cols, f, n, w);
        float value = 0.0;
        for (int i = 0; i < 4; i++) {
            if (i >= n) break;
            value += pick(w, i) * lattice(offset + r * cols + f + i, c, s);
        }
        total += amplitude * value;
        amplitude *= 0.5;
        offset += 14 * cols;
    }
    return total;
}

vec3 wallpaper(vec2 uv) {
    float phase = u_time * TURN;
    float c = cos(phase);
    float s = sin(phase);
    float y = uv.y * u_size.y;
    float spacing = u_size.y / 12.0;
    float half_width = max(1.0, floor(u_size.y / 720.0 + 0.5)) * 0.5;
    float fill = 0.0;
    float line = 0.0;
    // Front to back: the nearest ridge whose silhouette covers the pixel.
    for (int r = 13; r >= 0; r--) {
        float low = rangeAt(r * 2);
        float high = rangeAt(r * 2 + 1);
        float profile = (ridge(uv.x, r, c, s) - low) / max(high - low, 1e-6);
        float top = spacing * float(r + 1) - profile * profile * profile * spacing * 5.0;
        if (y >= top - half_width - 0.5) {
            line = 1.0 - smoothstep(half_width - 0.5, half_width + 0.5, abs(y - top));
            if (y > top && (r == 0 || r == 3 || r == 6 || r == 9 || r == 12))
                fill = 60.0 / 255.0;
            break;
        }
    }
    return compose(uv, fill, line, u_reach);
}
