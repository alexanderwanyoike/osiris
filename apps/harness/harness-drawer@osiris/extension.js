// Keeps the Harness at the right edge of the screen, full height, above other
// windows, and slides it in and out. GTK4 on X11 gives an application no way
// to place its own window; where the Harness sits will become the Skin's
// choice (CONTEXT.md).
//
// The Harness asks for Close over D-Bus rather than hiding itself, so the
// window can slide away before it is minimised. Opening is the app's own
// present(), which unminimises it and slides it back.

const Gio = imports.gi.Gio;
const Clutter = imports.gi.Clutter;
const Meta = imports.gi.Meta;

const APP_ID = 'dev.osiris.Harness';
// Matches WIDTH in apps/harness/main.py.
const WIDTH = 440;
const SLIDE_MS = 220;

const BUS_NAME = 'dev.osiris.HarnessDrawer';
const OBJECT_PATH = '/dev/osiris/HarnessDrawer';

const INTERFACE = `
<node>
  <interface name="${BUS_NAME}">
    <method name="Close"/>
  </interface>
</node>`;

let drawer = null;

class Drawer {
    constructor() {
        this._windows = new Map();
        this._created = global.display.connect(
            'window-created', (_display, window) => this._adopt(window));
        for (let actor of global.get_window_actors())
            this._adopt(actor.meta_window);
        this._dbus = Gio.DBusExportedObject.wrapJSObject(INTERFACE, this);
        this._dbus.export(Gio.DBus.session, OBJECT_PATH);
        this._owner = Gio.bus_own_name_on_connection(
            Gio.DBus.session, BUS_NAME, Gio.BusNameOwnerFlags.NONE, null, null);
    }

    _adopt(window) {
        if (!window || this._windows.has(window) ||
            window.get_gtk_application_id() !== APP_ID)
            return;
        this._windows.set(window, [
            window.connect('notify::minimized', () => {
                if (!window.minimized)
                    this._slideIn(window);
            }),
            window.connect('unmanaged', () => this._windows.delete(window)),
        ]);
        window.make_above();
        window.stick();
        // The window's actor does not exist yet when it is created.
        Meta.later_add(Meta.LaterType.BEFORE_REDRAW, () => {
            this._slideIn(window);
            return false;
        });
    }

    _place(window) {
        let area = window.get_work_area_for_monitor(window.get_monitor());
        window.move_resize_frame(
            true, area.x + area.width - WIDTH, area.y, WIDTH, area.height);
    }

    _slideIn(window) {
        let actor = window.get_compositor_private();
        if (!actor)
            return;
        this._place(window);
        actor.remove_all_transitions();
        actor.translation_x = WIDTH;
        actor.ease({
            translation_x: 0,
            duration: SLIDE_MS,
            mode: Clutter.AnimationMode.EASE_OUT_QUAD,
        });
    }

    CloseAsync(params, invocation) {
        for (let window of this._windows.keys()) {
            let actor = window.get_compositor_private();
            if (!actor || window.minimized)
                continue;
            actor.ease({
                translation_x: WIDTH,
                duration: SLIDE_MS,
                mode: Clutter.AnimationMode.EASE_IN_QUAD,
                // Left off-screen: unminimising slides it back from there.
                onStopped: () => window.minimize(),
            });
        }
        invocation.return_value(null);
    }

    destroy() {
        global.display.disconnect(this._created);
        for (let [window, ids] of this._windows) {
            for (let id of ids)
                window.disconnect(id);
            let actor = window.get_compositor_private();
            if (actor)
                actor.translation_x = 0;
        }
        this._windows.clear();
        this._dbus.unexport();
        Gio.bus_unown_name(this._owner);
    }
}

function init(metadata) {
}

function enable() {
    drawer = new Drawer();
}

function disable() {
    if (drawer) {
        drawer.destroy();
        drawer = null;
    }
}
