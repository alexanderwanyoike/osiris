"""Follow ~/.config/gtk-4.0/gtk.css as the Theme engine rewrites it."""

from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

#: A file finished being written, or one put in its place or taken away;
#: anything else may be a file still half written.
WRITTEN = (
    Gio.FileMonitorEvent.CHANGES_DONE_HINT,
    Gio.FileMonitorEvent.CREATED,
    Gio.FileMonitorEvent.DELETED,
)


class UserCss:
    #: Above the copy GTK itself read at startup, which never reloads.
    PRIORITY = Gtk.STYLE_PROVIDER_PRIORITY_USER + 1

    def __init__(self, sheet: Path) -> None:
        self._sheet = sheet
        self.provider = Gtk.CssProvider()
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, self.provider, self.PRIORITY
            )
        self._monitor = Gio.File.new_for_path(str(sheet)).monitor_file(
            Gio.FileMonitorFlags.NONE, None
        )
        self._monitor.connect("changed", self._changed)
        self.reload()

    def _changed(
        self, _monitor: object, _file: object, _other: object, event: object
    ) -> None:
        if event in WRITTEN:
            self.reload()

    def reload(self) -> None:
        try:
            self.provider.load_from_path(str(self._sheet))
        except GLib.Error:
            self.provider.load_from_string("")
