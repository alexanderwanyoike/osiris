// Fades from one theme to the next. See docs/adr/0014.
//
// The switcher calls Freeze, which covers the screen with a picture of itself
// and returns once that picture is on screen. The switch then happens beneath
// it, and Release fades the picture away.

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const Clutter = imports.gi.Clutter;
const Cinnamon = imports.gi.Cinnamon;
const Cogl = imports.gi.Cogl;
const GdkPixbuf = imports.gi.GdkPixbuf;

const BUS_NAME = 'dev.osiris.Transition';
const OBJECT_PATH = '/dev/osiris/Transition';

// A switcher that dies between Freeze and Release must not leave the desktop
// frozen behind a picture of itself.
const RELEASE_ANYWAY_MS = 5000;

const INTERFACE = `
<node>
  <interface name="${BUS_NAME}">
    <method name="Freeze"/>
    <method name="Release">
      <arg type="u" name="delay" direction="in"/>
      <arg type="u" name="duration" direction="in"/>
    </method>
  </interface>
</node>`;

let transition = null;

class Transition {
    constructor() {
        this._cover = null;
        this._picture = null;
        this._timeouts = [];
        this._dbus = Gio.DBusExportedObject.wrapJSObject(INTERFACE, this);
        this._dbus.export(Gio.DBus.session, OBJECT_PATH);
        this._owner = Gio.bus_own_name_on_connection(
            Gio.DBus.session, BUS_NAME, Gio.BusNameOwnerFlags.NONE, null, null);
    }

    FreezeAsync(params, invocation) {
        this._clear();
        this._picture = GLib.build_filenamev([
            GLib.get_user_runtime_dir(), `osiris-transition-${Date.now()}.png`]);
        let screenshot = new Cinnamon.Screenshot();
        screenshot.screenshot(false, this._picture, (source, success) => {
            if (success)
                this._cover = this._showCover(this._picture);
            // Answered either way: without the picture the switch still
            // applies, it just is not hidden.
            this._later(() => invocation.return_value(null));
        });
    }

    Release(delay, duration) {
        let cover = this._cover;
        if (!cover)
            return;
        this._after(delay, () => {
            cover.ease({
                opacity: 0,
                duration: duration,
                mode: Clutter.AnimationMode.EASE_OUT_QUAD,
                onComplete: () => this._clear(),
            });
        });
    }

    // Loaded here rather than as a CSS background-image, which St loads
    // asynchronously: the cover would still be empty when Freeze answers.
    _showCover(path) {
        let pixbuf = GdkPixbuf.Pixbuf.new_from_file(path);
        let image = new Clutter.Image();
        image.set_data(pixbuf.get_pixels(),
                       pixbuf.get_has_alpha() ? Cogl.PixelFormat.RGBA_8888
                                              : Cogl.PixelFormat.RGB_888,
                       pixbuf.get_width(), pixbuf.get_height(),
                       pixbuf.get_rowstride());
        let cover = new Clutter.Actor({
            x: 0, y: 0,
            width: global.stage.width, height: global.stage.height,
            content: image,
            reactive: true,
        });
        global.stage.add_child(cover);
        global.stage.set_child_above_sibling(cover, null);
        this._after(RELEASE_ANYWAY_MS, () => this.Release(0, 150));
        return cover;
    }

    // Runs once the stage has painted, so whatever was just added is visible.
    _later(callback) {
        let id = global.stage.connect('after-paint', () => {
            global.stage.disconnect(id);
            callback();
        });
        global.stage.queue_redraw();
    }

    _after(milliseconds, callback) {
        let id = GLib.timeout_add(GLib.PRIORITY_DEFAULT, milliseconds, () => {
            this._timeouts = this._timeouts.filter(other => other !== id);
            callback();
            return GLib.SOURCE_REMOVE;
        });
        this._timeouts.push(id);
    }

    _clear() {
        this._timeouts.forEach(id => GLib.source_remove(id));
        this._timeouts = [];
        if (this._cover) {
            this._cover.destroy();
            this._cover = null;
        }
        if (this._picture) {
            GLib.unlink(this._picture);
            this._picture = null;
        }
    }

    destroy() {
        this._clear();
        Gio.bus_unown_name(this._owner);
        this._dbus.unexport();
    }
}

function init(metadata) {
}

function enable() {
    transition = new Transition();
}

function disable() {
    if (transition) {
        transition.destroy();
        transition = null;
    }
}
