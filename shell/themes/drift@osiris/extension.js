// Draws a drifting wallpaper live on the GPU. See shell/themes/drift.py.
//
// drift.py publishes the active theme's tones and the style's composition in
// STATE; this draws the style from them every frame in a fragment shader, so
// the wallpaper genuinely moves. The shader is wallpaper.py's wave() and
// compose() written again in GLSL: keep the two in step, or the moving
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

const STYLES = ['wave'];

const DECLARATIONS = `
uniform float u_time;
uniform float u_aspect;
uniform float u_core;
uniform vec3 u_base;
uniform vec3 u_shape;
uniform vec3 u_line;
uniform float u_line_alpha;
uniform float u_reach;
uniform float u_tilt;
uniform float u_offsets[18];
`;

// wallpaper.wave() then compose(), per pixel. u_time is the phase in turns.
const WAVE = `
const float TURN = 6.28318530718;
float x = cogl_tex_coord_in[0].x;
float y = cogl_tex_coord_in[0].y;
float fill = 0.0;
float line = 0.0;
for (int i = 0; i < 6; i++) {
    float centre = 0.76 + u_tilt * (x - 0.5)
        + 0.060 * sin(TURN * (0.55 * x + u_time) + u_offsets[i * 3])
        + 0.030 * sin(TURN * (1.35 * x - 2.0 * u_time) + u_offsets[i * 3 + 1])
        + 0.012 * sin(TURN * (2.70 * x + 3.0 * u_time) + u_offsets[i * 3 + 2]);
    float d = y - centre;
    float strength = 0.45 + 0.55 * (1.0 - abs(float(i) / 5.0 - 0.5) * 2.0);
    float core = d / u_core;
    float halo = d / 0.022;
    line += (exp(-core * core) + 0.18 * exp(-halo * halo)) * strength;
    if (d > 0.0)
        fill += exp(-d / 0.08) * 0.12;
}
fill = clamp(fill, 0.0, 1.0);
line = clamp(line, 0.0, 1.0);
float radius = length(vec2((x - 0.5) * u_aspect, y - 0.5));
float t = clamp(radius / u_reach, 0.0, 1.0);
float quiet = pow(t * t * (3.0 - 2.0 * t), 1.6);
fill *= quiet;
line *= quiet;
vec3 base = u_base * (1.0 - 0.12 * y);
vec3 colour = base + (u_shape - base) * fill;
colour = colour + (u_line - colour) * (line * u_line_alpha);
cogl_color_out = vec4(colour, 1.0);
`;

const WaveEffect = GObject.registerClass(
class WaveEffect extends Cinnamon.GLSLEffect {
    vfunc_build_pipeline() {
        this.add_glsl_snippet(Cinnamon.SnippetHook.FRAGMENT, DECLARATIONS, WAVE, true);
    }

    set(name, components, values) {
        this.set_uniform_float(this.get_uniform_location(name), components, values);
    }
});

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
            effect.set('u_base', 3, s.base);
            effect.set('u_shape', 3, s.shape);
            effect.set('u_line', 3, s.line);
            effect.set('u_line_alpha', 1, [s.line_alpha]);
            effect.set('u_reach', 1, [s.reach]);
            effect.set('u_tilt', 1, [s.tilt]);
            effect.set('u_offsets', 1, s.offsets);
            effect.set('u_aspect', 1, [view.monitor.width / view.monitor.height]);
            // One device pixel at 720p, scaling with the screen: wave()'s core.
            effect.set('u_core', 1, [Math.max(0.8, view.monitor.height * 0.0012) / view.monitor.height]);
        }
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
        for (let view of this._views) {
            view.effect.set('u_time', 1, [turn]);
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
            let effect = new WaveEffect();
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
