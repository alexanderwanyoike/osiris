// Draws a drifting wallpaper live on the GPU. See shell/themes/drift.py.
//
// drift.py publishes the active theme's tones and the style's composition in
// STATE; this draws the style from them every frame in a fragment shader, so
// the wallpaper genuinely moves. Each style is its renderer in wallpaper.py,
// and compose(), written again in GLSL: keep the two in step, or the moving
// wallpaper and the still one beneath it stop matching.
//
// The layer is the first child of global.bottom_window_group: Muffin never
// restacks that group on X11, and nemo-desktop's window in it is transparent,
// so the layer shows through the icons and stays under every window.

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const GObject = imports.gi.GObject;
const Clutter = imports.gi.Clutter;
const Cogl = imports.gi.Cogl;
const Cinnamon = imports.gi.Cinnamon;
const GdkPixbuf = imports.gi.GdkPixbuf;
const Main = imports.ui.main;
const ScreenSaver = imports.misc.screenSaver;

const HOME = GLib.get_home_dir();
const CACHE = GLib.build_filenamev([HOME, '.cache', 'osiris', 'drift']);
const CONFIG = GLib.build_filenamev([HOME, '.config', 'osiris']);
const STATE = GLib.build_filenamev([CACHE, 'current.json']);
const PREFERENCE = GLib.build_filenamev([CONFIG, 'drift']);
const THEME = GLib.build_filenamev([CONFIG, 'theme']);

// Every frame repaints the whole stage, windows included. Thirty a second is
// smooth for motion this slow. Muffin calls a software renderer accelerated,
// so rather than ask, the extension watches what Cinnamon spends and halves
// the rate while it is over BUDGET of a core, down to SLOWEST_MS.
const FASTEST_MS = 33;
const SLOWEST_MS = 500;
const BUDGET = 0.15;
const MEASURE_MS = 5000;
const FADE_MS = 1500;

// Index into the shader's styles; keep in step with drift.py's LOOPS.
const STYLES = ['wave', 'aurora', 'cells', 'dots', 'ridges'];

// Cogl compiles GLSL 1.20: no %, so a vec4's component is picked by hand.
const DECLARATIONS = `
uniform float u_style;
uniform float u_time;
uniform vec2 u_size;
uniform vec3 u_base;
uniform vec3 u_shape;
uniform vec3 u_line;
uniform float u_line_alpha;
uniform float u_reach;
uniform vec4 u_range[8];
uniform float u_tilt;
uniform float u_offsets[18];
uniform vec4 u_glow_a[4];
uniform vec4 u_glow_b[4];
uniform vec4 u_sites[24];
uniform vec2 u_cells;
uniform vec4 u_lat[11];
uniform vec4 u_par[11];
uniform vec4 u_rl[81];
uniform vec4 u_rp[81];

const float TURN = 6.28318530718;
float g_cos;
float g_sin;

float pick(vec4 v, int c) {
    if (c == 0) return v.x;
    if (c == 1) return v.y;
    if (c == 2) return v.z;
    return v.w;
}

float latticeAt(int i, int which) {
    int slot = i / 4;
    int c = i - slot * 4;
    if (which == 0) return pick(u_lat[slot], c) * g_cos + pick(u_par[slot], c) * g_sin;
    return pick(u_rl[slot], c) * g_cos + pick(u_rp[slot], c) * g_sin;
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
// edges included, so the live noise matches wallpaper._smooth exactly.
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

// One octave of the dots' noise: rows doubling, half as many columns.
float octave2(float u, float v, int rows, int cols, int offset) {
    int fx; int nx; vec4 wx;
    int fy; int ny; vec4 wy;
    taps(u, cols, fx, nx, wx);
    taps(v, rows, fy, ny, wy);
    float total = 0.0;
    for (int j = 0; j < 4; j++) {
        if (j >= ny) break;
        float row = 0.0;
        for (int i = 0; i < 4; i++) {
            if (i >= nx) break;
            row += pick(wx, i) * latticeAt(offset + (fy + j) * cols + fx + i, 0);
        }
        total += pick(wy, j) * row;
    }
    return total;
}

// One ridge's height along x: its row of each octave, interpolated in x.
float ridge(float u, int r) {
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
            value += pick(w, i) * latticeAt(offset + r * cols + f + i, 1);
        }
        total += amplitude * value;
        amplitude *= 0.5;
        offset += 14 * cols;
    }
    return total;
}
`;

// Each style is its renderer in wallpaper.py, per pixel; then compose().
const CODE = `
float x = cogl_tex_coord_in[0].x;
float y = cogl_tex_coord_in[0].y;
float phase = u_time * TURN;
g_cos = cos(phase);
g_sin = sin(phase);
vec2 px = vec2(x, y) * u_size;
float fill = 0.0;
float line = 0.0;

if (u_style < 0.5) {
    // wave
    float core = max(0.8, u_size.y * 0.0012) / u_size.y;
    for (int i = 0; i < 6; i++) {
        float centre = 0.76 + u_tilt * (x - 0.5)
            + 0.060 * sin(TURN * (0.55 * x + u_time) + u_offsets[i * 3])
            + 0.030 * sin(TURN * (1.35 * x - 2.0 * u_time) + u_offsets[i * 3 + 1])
            + 0.012 * sin(TURN * (2.70 * x + 3.0 * u_time) + u_offsets[i * 3 + 2]);
        float d = y - centre;
        float strength = 0.45 + 0.55 * (1.0 - abs(float(i) / 5.0 - 0.5) * 2.0);
        float c = d / core;
        float h = d / 0.022;
        line += (exp(-c * c) + 0.18 * exp(-h * h)) * strength;
        if (d > 0.0)
            fill += exp(-d / 0.08) * 0.12;
    }
    fill = clamp(fill, 0.0, 1.0);
    line = clamp(line, 0.0, 1.0);
} else if (u_style < 1.5) {
    // aurora
    float glow = 0.0;
    for (int i = 0; i < 4; i++) {
        vec4 a = u_glow_a[i];
        vec4 b = u_glow_b[i];
        float angle = a.x + 0.45 * (sin(phase + a.y) - sin(a.y));
        float dx = (x - 0.5 - cos(angle) * a.z) / b.x;
        float dy = (y - 0.5 - sin(angle) * a.w) / b.y;
        float light = exp(-(dx * dx + dy * dy));
        if (i == 2)
            glow = max(glow, light);
        else
            fill = max(fill, light);
    }
    fill *= 0.8;
    line = glow * 0.45;
} else if (u_style < 2.5) {
    // cells, in units of the height so both axes move alike
    float aspect = u_size.x / u_size.y;
    vec2 p = vec2(x * aspect, y);
    float reach = 0.25 / u_cells.y;
    float best = 1e9;
    float second = 1e9;
    vec2 near = vec2(0.0);
    vec2 next = vec2(0.0);
    for (int i = 0; i < 24; i++) {
        if (float(i) >= u_cells.x) break;
        vec4 s = u_sites[i];
        vec2 site = vec2(s.x * aspect, s.y)
            + reach * vec2(cos(phase + s.z) - cos(s.z), sin(phase + s.z) - sin(s.z));
        float d = dot(p - site, p - site);
        if (d < best) {
            second = best; next = near;
            best = d; near = site; fill = s.w;
        } else if (d < second) {
            second = d; next = site;
        }
    }
    // Lead along the bisector of the two nearest sites, a pixel wide.
    float edge = dot((near + next) * 0.5 - p, normalize(next - near)) * u_size.y;
    line = 1.0 - smoothstep(0.0, 1.0, edge);
} else if (u_style < 3.5) {
    // dots: a halftone grid sized by the noise at each dot's centre
    float stepPx = u_size.y / 30.0;
    vec2 cell = floor(px / stepPx);
    vec2 centre = (cell + 0.5) * stepPx;
    vec2 at = (min(floor(centre), u_size - 1.0) + 0.5) / u_size;
    float raw = octave2(at.x, at.y, 2, 2, 0)
        + 0.5 * octave2(at.x, at.y, 4, 2, 4)
        + 0.25 * octave2(at.x, at.y, 8, 4, 12);
    float value = (raw - rangeAt(0)) / max(rangeAt(1) - rangeAt(0), 1e-6);
    float radius = (value - 0.55) / 0.45 * stepPx * 0.22;
    if (radius > stepPx * 0.04)
        line = 1.0 - smoothstep(radius - 0.5, radius + 0.5, length(px - centre));
} else {
    // ridges, front to back: the nearest whose silhouette covers the pixel
    float spacing = u_size.y / 12.0;
    float half_width = max(1.0, floor(u_size.y / 720.0 + 0.5)) * 0.5;
    for (int r = 13; r >= 0; r--) {
        float low = rangeAt(r * 2);
        float high = rangeAt(r * 2 + 1);
        float profile = (ridge(x, r) - low) / max(high - low, 1e-6);
        float top = spacing * float(r + 1) - profile * profile * profile * spacing * 5.0;
        if (px.y >= top - half_width - 0.5) {
            line = 1.0 - smoothstep(half_width - 0.5, half_width + 0.5, abs(px.y - top));
            if (px.y > top && (r == 0 || r == 3 || r == 6 || r == 9 || r == 12))
                fill = 60.0 / 255.0;
            break;
        }
    }
}

float radius = length(vec2((x - 0.5) * u_size.x / u_size.y, y - 0.5));
float t = clamp(radius / u_reach, 0.0, 1.0);
float quiet = pow(t * t * (3.0 - 2.0 * t), 1.6);
fill *= quiet;
line *= quiet;
vec3 base = u_base * (1.0 - 0.12 * y);
vec3 colour = base + (u_shape - base) * fill;
colour = colour + (u_line - colour) * (line * u_line_alpha);
cogl_color_out = vec4(colour, 1.0);
`;

// Registered once per Cinnamon session: an extension that is disabled and
// enabled again runs this file again, and a GType cannot be registered twice.
if (!globalThis.osirisDriftEffect) {
    globalThis.osirisDriftEffect = GObject.registerClass(
    class OsirisDriftEffect extends Cinnamon.GLSLEffect {
        vfunc_build_pipeline() {
            this.add_glsl_snippet(Cinnamon.SnippetHook.FRAGMENT, DECLARATIONS, CODE, true);
        }

        set(name, components, values) {
            // Cogl takes whole components; a short last one is padded.
            let padded = values.slice();
            while (padded.length % components)
                padded.push(0);
            this.set_uniform_float(this.get_uniform_location(name), components, padded);
        }
    });
}
const DriftEffect = globalThis.osirisDriftEffect;

let drift = null;

function readText(path) {
    try {
        let [ok, bytes] = GLib.file_get_contents(path);
        return ok ? new TextDecoder().decode(bytes).trim() : null;
    } catch (e) {
        return null;
    }
}

// Seconds of CPU this process has used; the extension runs inside Cinnamon.
function cpuSeconds() {
    let stat = readText('/proc/self/stat');
    if (!stat)
        return null;
    let fields = stat.slice(stat.lastIndexOf(')') + 2).split(' ');
    // utime and stime, fields 14 and 15 of the whole line, in USER_HZ ticks.
    return (parseInt(fields[11]) + parseInt(fields[12])) / 100;
}

function shadersAvailable() {
    try {
        return Clutter.feature_available(Clutter.FeatureFlags.SHADERS_GLSL);
    } catch (e) {
        return true;
    }
}

class Drift {
    constructor() {
        this._state = null;
        this._logo = null;
        this._tick = 0;
        this._interval = FASTEST_MS;
        this._measured = null;
        this._screenSaverActive = false;
        this._target = 0;

        this._layer = new Clutter.Actor({ opacity: 0 });
        global.bottom_window_group.insert_child_at_index(this._layer, 0);
        this._views = [];
        this._buildMonitors();

        this._signals = [
            [Main.layoutManager, Main.layoutManager.connect(
                'monitors-changed', () => this._buildMonitors())],
            [global.display, global.display.connect(
                'in-fullscreen-changed', () => this._update())],
        ];

        this._screenSaver = new ScreenSaver.ScreenSaverProxy();
        this._screenSaverSignal = this._screenSaver.connectSignal(
            'ActiveChanged', (proxy, sender, [active]) => {
                this._screenSaverActive = active;
                this._update();
            });

        this._watches = [CACHE, CONFIG].map(path => {
            GLib.mkdir_with_parents(path, 0o755);
            let monitor = Gio.File.new_for_path(path).monitor_directory(
                Gio.FileMonitorFlags.NONE, null);
            monitor.connect('changed', () => this._soon());
            return monitor;
        });
        this._debounce = 0;
        this._reload();
    }

    // Several files change at once when a theme is applied; read them once.
    _soon() {
        if (this._debounce)
            GLib.source_remove(this._debounce);
        this._debounce = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 250, () => {
            this._debounce = 0;
            this._reload();
            return GLib.SOURCE_REMOVE;
        });
    }

    _reload() {
        let state = null;
        try {
            state = JSON.parse(readText(STATE));
        } catch (e) {
            state = null;
        }
        // The state can outlive a theme switch by a moment; a wallpaper is
        // only drawn over the theme it belongs to.
        if (!state || !STYLES.includes(state.style) || !shadersAvailable() ||
            readText(PREFERENCE) === 'off' || readText(THEME) !== state.theme)
            state = null;
        if (JSON.stringify(state) !== JSON.stringify(this._state)) {
            this._state = state;
            if (state) {
                this._configure();
                this._loadLogo(state.logo);
            }
        }
        this._update();
    }

    _configure() {
        let s = this._state;
        for (let view of this._views) {
            let effect = view.effect;
            effect.set('u_style', 1, [STYLES.indexOf(s.style)]);
            effect.set('u_size', 2, [view.monitor.width, view.monitor.height]);
            for (let name in s.uniforms) {
                let [components, values] = s.uniforms[name];
                effect.set(name, components, values);
            }
        }
    }

    // A noise style's range at this point of the loop, between the two
    // measured either side of it.
    _range(turn) {
        let ranges = this._state.ranges;
        if (!ranges)
            return null;
        let position = turn * ranges.length;
        let i = Math.floor(position) % ranges.length;
        let j = (i + 1) % ranges.length;
        let t = position - Math.floor(position);
        return ranges[i].map((value, k) => value + (ranges[j][k] - value) * t);
    }

    _paused() {
        if (this._screenSaverActive)
            return true;
        for (let i = 0; i < global.display.get_n_monitors(); i++) {
            if (global.display.get_monitor_in_fullscreen(i))
                return true;
        }
        return false;
    }

    _update() {
        let run = this._state !== null && !this._paused();
        if (run && !this._tick) {
            this._measured = null;
            this._schedule();
            this._step();
        } else if (!run && this._tick) {
            GLib.source_remove(this._tick);
            this._tick = 0;
        }
        this._fade(this._state === null ? 0 : 255);
    }

    _schedule() {
        if (this._tick)
            GLib.source_remove(this._tick);
        this._tick = GLib.timeout_add(GLib.PRIORITY_DEFAULT, this._interval, () => {
            this._step();
            this._pace();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _step() {
        if (this._state === null)
            return;
        let loop = this._state.loop;
        let turn = ((Date.now() / 1000) % loop) / loop;
        let range = this._range(turn);
        for (let view of this._views) {
            view.effect.set('u_time', 1, [turn]);
            if (range)
                view.effect.set('u_range', 4, range);
            view.effect.queue_repaint();
        }
    }

    _pace() {
        let now = GLib.get_monotonic_time() / 1e6;
        let cpu = cpuSeconds();
        if (cpu === null)
            return;
        if (!this._measured) {
            this._measured = [now, cpu];
            return;
        }
        let [then, before] = this._measured;
        if ((now - then) * 1000 < MEASURE_MS)
            return;
        this._measured = [now, cpu];
        let share = (cpu - before) / (now - then);
        let interval = this._interval;
        if (share > BUDGET)
            interval = Math.min(SLOWEST_MS, interval * 2);
        else if (share < BUDGET / 3)
            interval = Math.max(FASTEST_MS, Math.round(interval / 2));
        if (interval !== this._interval) {
            this._interval = interval;
            this._schedule();
        }
    }

    _fade(opacity) {
        if (this._target === opacity)
            return;
        this._target = opacity;
        this._layer.ease({
            opacity: opacity,
            duration: FADE_MS,
            mode: Clutter.AnimationMode.EASE_IN_OUT_QUAD,
        });
    }

    _loadLogo(path) {
        this._logo = null;
        this._placeLogo();
        if (!path)
            return;
        let file = Gio.File.new_for_path(path);
        file.read_async(GLib.PRIORITY_LOW, null, (source, result) => {
            let stream;
            try {
                stream = source.read_finish(result);
            } catch (e) {
                return;
            }
            GdkPixbuf.Pixbuf.new_from_stream_async(stream, null, (s, done) => {
                stream.close(null);
                if (!this._state || this._state.logo !== path)
                    return;
                let pixbuf;
                try {
                    pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(done);
                } catch (e) {
                    return;
                }
                let image = new Clutter.Image();
                image.set_data(pixbuf.get_pixels(),
                               pixbuf.get_has_alpha() ? Cogl.PixelFormat.RGBA_8888
                                                      : Cogl.PixelFormat.RGB_888,
                               pixbuf.get_width(), pixbuf.get_height(),
                               pixbuf.get_rowstride());
                this._logo = { image: image, width: pixbuf.get_width(), height: pixbuf.get_height() };
                this._placeLogo();
            });
        });
    }

    // Scaled to fill each monitor and centred, as the still wallpaper is.
    _placeLogo() {
        for (let view of this._views) {
            if (!this._logo) {
                view.logo.content = null;
                continue;
            }
            let { width, height } = this._logo;
            let scale = Math.max(view.monitor.width / width, view.monitor.height / height);
            let w = Math.ceil(width * scale);
            let h = Math.ceil(height * scale);
            view.logo.set({
                x: Math.floor((view.monitor.width - w) / 2),
                y: Math.floor((view.monitor.height - h) / 2),
                width: w, height: h,
            });
            view.logo.content = this._logo.image;
        }
    }

    _buildMonitors() {
        this._layer.destroy_all_children();
        this._views = Main.layoutManager.monitors.map(monitor => {
            let frame = new Clutter.Actor({
                x: monitor.x, y: monitor.y,
                width: monitor.width, height: monitor.height,
                clip_to_allocation: true,
            });
            // Painted so the effect has something to draw over; the shader
            // replaces every pixel of it.
            let canvas = new Clutter.Actor({
                width: monitor.width, height: monitor.height,
                background_color: new Clutter.Color({ red: 0, green: 0, blue: 0, alpha: 255 }),
            });
            let effect = new DriftEffect();
            canvas.add_effect(effect);
            let logo = new Clutter.Actor();
            frame.add_child(canvas);
            frame.add_child(logo);
            this._layer.add_child(frame);
            return { monitor: monitor, effect: effect, logo: logo };
        });
        if (this._state)
            this._configure();
        this._placeLogo();
    }

    destroy() {
        if (this._tick)
            GLib.source_remove(this._tick);
        if (this._debounce)
            GLib.source_remove(this._debounce);
        this._watches.forEach(monitor => monitor.cancel());
        this._signals.forEach(([object, id]) => object.disconnect(id));
        this._screenSaver.disconnectSignal(this._screenSaverSignal);
        this._layer.destroy();
    }
}

function init(metadata) {
}

function enable() {
    drift = new Drift();
}

function disable() {
    if (drift) {
        drift.destroy();
        drift = null;
    }
}
