// Keeps a drifting wallpaper moving. See shell/themes/drift.py.
//
// drift.py renders the active theme's loop of frames and names it in STATE;
// this plays the loop by the clock, blending each frame into the next, on a
// layer beneath the desktop icons. The arithmetic is osiris/themes/frames.py's.
//
// The layer is the first child of global.bottom_window_group: Muffin never
// restacks that group on X11, and nemo-desktop's window in it is transparent,
// so the layer shows through the icons and stays under every window.

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const Clutter = imports.gi.Clutter;
const Cogl = imports.gi.Cogl;
const GdkPixbuf = imports.gi.GdkPixbuf;
const Main = imports.ui.main;
const ScreenSaver = imports.misc.screenSaver;

const HOME = GLib.get_home_dir();
const CACHE = GLib.build_filenamev([HOME, '.cache', 'osiris', 'drift']);
const CONFIG = GLib.build_filenamev([HOME, '.config', 'osiris']);
const STATE = GLib.build_filenamev([CACHE, 'current.json']);
const PREFERENCE = GLib.build_filenamev([CONFIG, 'drift']);
const THEME = GLib.build_filenamev([CONFIG, 'theme']);

// Every tick repaints the whole stage, windows included. The motion is slow
// enough that four a second is smooth. Muffin calls a software renderer
// accelerated, so rather than ask, the extension watches what Cinnamon spends
// and halves the rate while it is over BUDGET of a core, down to SLOWEST_MS.
const FASTEST_MS = 250;
const SLOWEST_MS = 2000;
const BUDGET = 0.15;
const MEASURE_MS = 10000;
const FADE_MS = 1500;
// A frame not rendered yet is asked for again after this, not every tick.
const RETRY_MS = 2000;

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

class Drift {
    constructor() {
        this._state = null;
        this._generation = 0;
        this._images = new Map();
        this._loading = new Set();
        this._failed = new Map();
        this._shown = [null, null];
        this._tick = 0;
        this._interval = FASTEST_MS;
        this._measured = null;
        this._screenSaverActive = false;

        this._layer = new Clutter.Actor({ opacity: 0 });
        this._target = 0;
        global.bottom_window_group.insert_child_at_index(this._layer, 0);
        this._pairs = [];
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
        // The state can outlive a theme switch by a few seconds; a loop is
        // only played over the theme it belongs to.
        if (!state || readText(PREFERENCE) === 'off' || readText(THEME) !== state.theme)
            state = null;
        if (JSON.stringify(state) !== JSON.stringify(this._state)) {
            this._state = state;
            this._generation++;
            this._images.clear();
            this._loading.clear();
            this._failed.clear();
            this._shown = [null, null];
        }
        this._update();
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
        if (this._state === null)
            this._fade(0);
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
            interval = Math.max(FASTEST_MS, interval / 2);
        if (interval !== this._interval) {
            this._interval = interval;
            this._schedule();
        }
    }

    _due() {
        let { loop, count } = this._state;
        let position = ((Date.now() / 1000) % loop) / loop * count;
        let index = Math.floor(position);
        return [index, (index + 1) % count, position - index];
    }

    _step() {
        if (this._state === null)
            return;
        let [index, next, amount] = this._due();
        let count = this._state.count;
        [index, next, (next + 1) % count].forEach(i => this._load(i));
        for (let i of this._images.keys()) {
            if (i !== index && i !== next && i !== (next + 1) % count)
                this._images.delete(i);
        }

        let under = this._images.get(index);
        let over = this._images.get(next);
        if (!under) {
            this._fade(0);
            return;
        }
        if (this._shown[0] !== index || this._shown[1] !== (over ? next : null)) {
            this._shown = [index, over ? next : null];
            for (let [, back, front] of this._pairs) {
                back.content = under.image;
                front.content = over ? over.image : null;
            }
            this._cover(under.width, under.height);
        }
        let opacity = over ? Math.round(amount * 255) : 0;
        for (let [, , front] of this._pairs)
            front.opacity = opacity;
        this._fade(255);
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

    _load(index) {
        if (this._images.has(index) || this._loading.has(index))
            return;
        let failed = this._failed.get(index);
        if (failed && Date.now() - failed < RETRY_MS)
            return;
        let name = `frame-${String(index).padStart(3, '0')}.jpg`;
        let file = Gio.File.new_for_path(GLib.build_filenamev([this._state.dir, name]));
        let generation = this._generation;
        this._loading.add(index);
        let fail = () => {
            this._loading.delete(index);
            this._failed.set(index, Date.now());
        };
        // Decoded off the main loop: a frame is a few megapixels, and this is
        // the compositor's thread.
        file.read_async(GLib.PRIORITY_LOW, null, (source, result) => {
            let stream;
            try {
                stream = source.read_finish(result);
            } catch (e) {
                fail();
                return;
            }
            GdkPixbuf.Pixbuf.new_from_stream_async(stream, null, (s, done) => {
                stream.close(null);
                if (generation !== this._generation)
                    return;
                let pixbuf;
                try {
                    pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(done);
                } catch (e) {
                    fail();
                    return;
                }
                this._loading.delete(index);
                let image = new Clutter.Image();
                image.set_data(pixbuf.get_pixels(),
                               pixbuf.get_has_alpha() ? Cogl.PixelFormat.RGBA_8888
                                                      : Cogl.PixelFormat.RGB_888,
                               pixbuf.get_width(), pixbuf.get_height(),
                               pixbuf.get_rowstride());
                this._images.set(index, {
                    image: image,
                    width: pixbuf.get_width(),
                    height: pixbuf.get_height(),
                });
                this._step();
            });
        });
    }

    _buildMonitors() {
        this._layer.destroy_all_children();
        this._pairs = Main.layoutManager.monitors.map(monitor => {
            let frame = new Clutter.Actor({
                x: monitor.x, y: monitor.y,
                width: monitor.width, height: monitor.height,
                clip_to_allocation: true,
            });
            let back = new Clutter.Actor();
            let front = new Clutter.Actor({ opacity: 0 });
            frame.add_child(back);
            frame.add_child(front);
            this._layer.add_child(frame);
            return [monitor, back, front];
        });
        this._shown = [null, null];
    }

    // Scaled to fill each monitor and centred, the way the desktop's own
    // "zoom" places a wallpaper.
    _cover(width, height) {
        for (let [monitor, back, front] of this._pairs) {
            let scale = Math.max(monitor.width / width, monitor.height / height);
            let w = Math.ceil(width * scale);
            let h = Math.ceil(height * scale);
            let x = Math.floor((monitor.width - w) / 2);
            let y = Math.floor((monitor.height - h) / 2);
            for (let actor of [back, front])
                actor.set({ x: x, y: y, width: w, height: h });
        }
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
