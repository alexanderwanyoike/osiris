// Draws a drifting wallpaper live on the GPU. See shell/themes/drift.py.
//
// drift.py names the active theme's wallpaper package in STATE, with the
// theme's colours and what the package's still.py hands its shader; this
// compiles the package's shader after the prelude and draws it every frame,
// so the wallpaper genuinely moves. The still one stays beneath, and shows
// whenever this is not drawing.
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
const UNSUPPORTED = GLib.build_filenamev([CACHE, 'unsupported']);
const PREFERENCE = GLib.build_filenamev([CONFIG, 'drift']);
const THEME = GLib.build_filenamev([CONFIG, 'theme']);

// Every frame repaints the whole stage, windows included. Thirty a second is
// smooth for motion this slow. Muffin calls a software renderer accelerated,
// so rather than ask, the extension watches what Cinnamon spends and halves
// the rate while it is over BUDGET of a core, down to SLOWEST_MS. Still over
// budget there, the machine has no GPU to speak of: the still wallpaper is
// left showing for the rest of the session, and UNSUPPORTED says why.
const FASTEST_MS = 33;
const SLOWEST_MS = 500;
const BUDGET = 0.15;
const MEASURE_MS = 5000;
const FADE_MS = 1500;

// The body of the fragment snippet: osiris/themes/wallpapers.py's CODE, which
// is also what a package's shader is checked against.
const CODE = 'cogl_color_out = vec4(wallpaper(cogl_tex_coord_in[0].xy), 1.0);';

// One effect class per shader, kept for the Cinnamon session: Cogl builds a
// class's pipeline once, and an extension that is disabled and enabled again
// runs this file again, when a GType cannot be registered twice.
globalThis.osirisDriftEffects = globalThis.osirisDriftEffects || new Map();

function effectFor(declarations) {
    let key = GLib.compute_checksum_for_string(GLib.ChecksumType.SHA1, declarations, -1);
    if (!globalThis.osirisDriftEffects.has(key)) {
        globalThis.osirisDriftEffects.set(key, GObject.registerClass({
            GTypeName: `OsirisDriftEffect_${key.slice(0, 16)}`,
        }, class extends Cinnamon.GLSLEffect {
            vfunc_build_pipeline() {
                this.add_glsl_snippet(Cinnamon.SnippetHook.FRAGMENT, declarations, CODE, true);
            }

            set(name, components, values) {
                // Cogl takes whole components; a short last one is padded.
                let padded = values.slice();
                while (padded.length % components)
                    padded.push(0);
                this.set_uniform_float(this.get_uniform_location(name), components, padded);
            }
        }));
    }
    return globalThis.osirisDriftEffects.get(key);
}

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
        this._effect = null;
        this._theme = readText(THEME);
        // Each session finds out afresh; a new GPU or driver may change it.
        this._unsupported = false;
        GLib.unlink(UNSUPPORTED);

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

    // Several files change at once when a theme is applied; read them once,
    // and soon: a switch holds its frozen picture for only 400ms.
    _soon() {
        if (this._debounce)
            GLib.source_remove(this._debounce);
        this._debounce = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 100, () => {
            this._debounce = 0;
            this._reload();
            return GLib.SOURCE_REMOVE;
        });
    }

    _reload() {
        // A theme switch happens beneath the transition's frozen picture, so
        // the wallpaper changes at once with everything else; only the Drift
        // switch, seen as it happens, fades.
        let theme = readText(THEME);
        let instant = theme !== this._theme;
        this._theme = theme;
        let state = null;
        try {
            state = JSON.parse(readText(STATE));
        } catch (e) {
            state = null;
        }
        // The state can outlive a theme switch by a moment; a wallpaper is
        // only drawn over the theme it belongs to.
        if (!state || state.problem || this._unsupported || !shadersAvailable() ||
            readText(PREFERENCE) === 'off' || readText(THEME) !== state.theme)
            state = null;
        if (JSON.stringify(state) !== JSON.stringify(this._state)) {
            this._state = state;
            if (state) {
                let prelude = readText(state.prelude);
                let shader = readText(state.shader);
                this._effect = prelude && shader ? effectFor(`${prelude}\n${shader}\n`) : null;
                if (!this._effect)
                    this._state = null;
                else {
                    this._buildMonitors();
                    this._loadLogo(state.logo);
                }
            }
        }
        this._update(instant);
    }

    _configure() {
        let s = this._state;
        for (let view of this._views) {
            let effect = view.effect;
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

    _update(instant = false) {
        let run = this._state !== null && !this._paused();
        if (run && !this._tick) {
            this._measured = null;
            this._schedule();
            this._step();
        } else if (!run && this._tick) {
            GLib.source_remove(this._tick);
            this._tick = 0;
        }
        this._fade(this._state === null ? 0 : 255, instant);
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
        if (share > BUDGET && interval === SLOWEST_MS) {
            this._giveUp();
            return;
        }
        if (share > BUDGET)
            interval = Math.min(SLOWEST_MS, interval * 2);
        else if (share < BUDGET / 3)
            interval = Math.max(FASTEST_MS, Math.round(interval / 2));
        if (interval !== this._interval) {
            this._interval = interval;
            this._schedule();
        }
    }

    _giveUp() {
        this._unsupported = true;
        try {
            GLib.file_set_contents(UNSUPPORTED,
                'Moving wallpapers need a graphics card; showing the still one instead.\n');
        } catch (e) {
            logError(e, 'drift@osiris');
        }
        this._reload();
    }

    _fade(opacity, instant = false) {
        if (instant) {
            this._layer.remove_all_transitions();
            this._layer.opacity = opacity;
            this._target = opacity;
            return;
        }
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
            let effect = this._effect ? new this._effect() : null;
            if (effect)
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
