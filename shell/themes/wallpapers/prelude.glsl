// Declared before every wallpaper's shader.glsl; see osiris/themes/wallpapers.py.
// Cogl compiles GLSL 1.20: no %, no bitwise operators, no newer built-ins.

// Where the loop is, from 0 to 1, and the monitor in device pixels.
uniform float u_time;
uniform vec2 u_size;

// The theme. The tones are the wallpaper's own (wallpaper.tones); the rest is
// the palette as the theme declares it. u_dark is 1.0 for a dark theme.
uniform vec3 u_base;
uniform vec3 u_shape;
uniform vec3 u_line;
uniform vec3 u_ink;
uniform float u_line_alpha;
uniform vec3 u_background;
uniform vec3 u_surface;
uniform vec3 u_foreground;
uniform vec3 u_accent;
uniform vec3 u_accent_muted;
uniform vec3 u_success;
uniform vec3 u_warning;
uniform vec3 u_danger;
uniform float u_dark;

// Up to 32 values still.py measured round the loop (its ranges()), already
// interpolated to u_time.
uniform vec4 u_range[8];

const float TURN = 6.28318530718;

float pick(vec4 v, int c) {
    if (c == 0) return v.x;
    if (c == 1) return v.y;
    if (c == 2) return v.z;
    return v.w;
}

float rangeAt(int i) {
    return pick(u_range[i / 4], i - (i / 4) * 4);
}

// Keys' cubic with a = -0.5, which is Pillow's BICUBIC.
float keys(float x) {
    x = abs(x);
    if (x < 1.0) return (1.5 * x - 2.5) * x * x + 1.0;
    if (x < 2.0) return ((-0.5 * x + 2.5) * x - 4.0) * x + 2.0;
    return 0.0;
}

// The taps and weights Pillow uses to upsample n samples to coordinate u,
// edges included, so noise matches wallpaper._smooth exactly.
void taps(float u, int n, out int first, out int count, out vec4 w) {
    float centre = u * float(n);
    first = int(centre - 1.5);
    if (first < 0) first = 0;
    int last = int(centre + 2.5);
    if (last > n) last = n;
    count = last - first;
    float o = float(first) - centre + 0.5;
    w = vec4(keys(o), keys(o + 1.0), keys(o + 2.0), keys(o + 3.0));
    if (count < 4) w.w = 0.0;
    if (count < 3) w.z = 0.0;
    if (count < 2) w.y = 0.0;
    w /= (w.x + w.y + w.z + w.w);
}

// wallpaper.compose(): the quiet centre, the slow gradient, the shape tone
// under `fill` and the line work under `line`. The mark is drawn above.
vec3 compose(vec2 uv, float fill, float line, float reach) {
    float radius = length(vec2((uv.x - 0.5) * u_size.x / u_size.y, uv.y - 0.5));
    float t = clamp(radius / reach, 0.0, 1.0);
    float quiet = pow(t * t * (3.0 - 2.0 * t), 1.6);
    vec3 base = u_base * (1.0 - 0.12 * uv.y);
    vec3 colour = base + (u_shape - base) * (fill * quiet);
    return colour + (u_line - colour) * (line * quiet * u_line_alpha);
}
