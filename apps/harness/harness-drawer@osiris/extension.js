// Keeps the Harness at the right edge of the screen, full height, above other
// windows, and slides it in and out. A width the person drags to is kept.
// Expanded, it fills the screen above the dock: Plank reserves no space in
// intelligent-hide mode, so a drawer covering it would hide it. Plank's window
// spans the whole width with zoom headroom above the visible bar, so this
// only applies when expanded; the narrow drawer at the edge keeps its height. GTK4 on X11 gives an application no way
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
    <method name="Expand">
      <arg type="b" name="expanded" direction="in"/>
    </method>
  </interface>
</node>`;

let drawer = null;

class Drawer {
    constructor() {
        this._windows = new Map();
        this._widths = new Map();
        this._expanded = new Set();
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
            window.connect('size-changed', () => this._remember(window)),
            window.connect('unmanaged', () => {
                this._windows.delete(window);
                this._widths.delete(window);
                this._expanded.delete(window);
            }),
        ]);
        window.make_above();
        window.stick();
        // The window's actor does not exist yet when it is created.
        Meta.later_add(Meta.LaterType.BEFORE_REDRAW, () => {
            this._slideIn(window);
            return false;
        });
    }

    _remember(window) {
        if (window.get_maximized() || window.minimized || this._expanded.has(window))
            return;
        this._widths.set(window, window.get_frame_rect().width);
    }

    // The top of the highest dock overlapping [left, right), or the bottom of
    // the work area when none does.
    _floor(area, left, right) {
        let floor = area.y + area.height;
        for (let actor of global.get_window_actors()) {
            let other = actor.meta_window;
            if (other.get_window_type() !== Meta.WindowType.DOCK)
                continue;
            let rect = other.get_frame_rect();
            if (rect.x < right && rect.x + rect.width > left && rect.y > area.y)
                floor = Math.min(floor, rect.y);
        }
        return floor;
    }

    _place(window) {
        if (window.get_maximized())
            return;
        let area = window.get_work_area_for_monitor(window.get_monitor());
        let width = this._expanded.has(window)
            ? area.width : (this._widths.get(window) || WIDTH);
        let left = area.x + area.width - width;
        let floor = this._expanded.has(window)
            ? this._floor(area, left, left + width) : area.y + area.height;
        window.move_resize_frame(true, left, area.y, width, floor - area.y);
    }

    ExpandAsync(params, invocation) {
        let [expanded] = params;
        for (let window of this._windows.keys()) {
            if (expanded)
                this._expanded.add(window);
            else
                this._expanded.delete(window);
            this._place(window);
        }
        invocation.return_value(null);
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
