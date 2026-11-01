"""The / and @ picker on the message box (#153).

What opens it, what it lists and where picked entries stand in the text are
decided in osiris/harness/picker.py; this draws the list at the cursor and
puts the chosen entry into the message.
"""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk, Pango  # noqa: E402

from osiris.harness.picker import Entry, matching, trigger  # noqa: E402

#: Rows shown at once; typing narrows the rest.
SHOWN = 8


class Picker:
    def __init__(self, entry: Gtk.TextView, offered: Callable[[str], list[Entry]]):
        self._entry = entry
        self._offered = offered
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.BROWSE)
        self.list.add_css_class("harness-picker")
        # Without autohide the popover leaves the keyboard with the message
        # box, so typing carries on filtering while it is open.
        self.popover = Gtk.Popover(child=self.list, autohide=False, has_arrow=False,
                                   position=Gtk.PositionType.TOP)
        self.popover.add_css_class("harness-picker-popover")
        self.popover.set_parent(entry)
        entry.get_buffer().connect("changed", lambda _b: self._typed())

    def _typed(self) -> None:
        buffer = self._entry.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        cursor = buffer.get_property("cursor-position")
        found = trigger(text, cursor)
        entries = matching(self._offered(found.sign), found.query) if found else []
        if not entries:
            self.popover.popdown()
            return
        self.list.remove_all()
        for entry in entries[:SHOWN]:
            self.list.append(_row(entry))
        self.list.select_row(self.list.get_row_at_index(0))
        self._point_at(buffer.get_iter_at_offset(found.start))
        self.popover.popup()

    def _point_at(self, where: Gtk.TextIter) -> None:
        place = self._entry.get_iter_location(where)
        x, y = self._entry.buffer_to_window_coords(
            Gtk.TextWindowType.WIDGET, place.x, place.y)
        point = Gdk.Rectangle()
        point.x, point.y, point.width, point.height = x, y, 1, place.height
        self.popover.set_pointing_to(point)


def _row(entry: Entry) -> Gtk.ListBoxRow:
    line = Gtk.Box(spacing=10)
    label = Gtk.Label(label=entry.label, xalign=0, ellipsize=Pango.EllipsizeMode.START)
    label.add_css_class("harness-picker-label")
    line.append(label)
    if entry.description:
        about = Gtk.Label(label=entry.description, xalign=0, hexpand=True,
                          ellipsize=Pango.EllipsizeMode.END)
        about.add_css_class("harness-meta")
        line.append(about)
    row = Gtk.ListBoxRow(child=line)
    row.entry = entry
    return row
