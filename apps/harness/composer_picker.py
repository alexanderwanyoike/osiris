"""The / and @ picker on the message box (#153).

What opens it, what it lists and where picked entries stand in the text are
decided in osiris/harness/picker.py; this draws the list at the cursor and
puts the chosen entry into the message.
"""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk, Pango  # noqa: E402

from osiris.harness.picker import (  # noqa: E402
    SIGN,
    Entry,
    Reference,
    matching,
    references,
    trigger,
)

#: Rows shown at once; typing narrows the rest.
SHOWN = 8
WIDTH = 440
MOVES = {Gdk.KEY_Down: 1, Gdk.KEY_Up: -1}
COMPLETES = (Gdk.KEY_Tab, Gdk.KEY_Return, Gdk.KEY_KP_Enter)


class Picker:
    def __init__(self, entry: Gtk.TextView, offered: Callable[[str], list[Entry]]):
        self._entry = entry
        self._offered = offered
        self._picked: list[Entry] = []
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.BROWSE)
        self.list.add_css_class("harness-picker")
        # One width whatever is listed, so the card holds still while typing
        # narrows it; descriptions are cut to fit rather than widen it.
        self.list.set_size_request(WIDTH, -1)
        self.list.connect("row-activated", lambda _l, row: self._complete(row.entry))
        # Without autohide the popover leaves the keyboard with the message
        # box, so typing carries on filtering while it is open.
        self.popover = Gtk.Popover(child=self.list, autohide=False, has_arrow=False,
                                   position=Gtk.PositionType.TOP)
        self.popover.add_css_class("harness-picker-popover")
        self.popover.set_parent(entry)
        self.token = entry.get_buffer().create_tag("harness-token", weight=500)
        entry.get_buffer().connect("changed", lambda _b: self._typed())
        # Captured before the message box sees them, so Enter picks an entry
        # rather than sending while the picker is open.
        keys = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self.key)
        entry.add_controller(keys)

    def restyle(self, colours: tuple[str, str]) -> None:
        """The Theme's token colours, foreground and background."""
        self.token.props.foreground, self.token.props.background = colours

    def references(self, text: str) -> tuple[Reference, ...]:
        """What was picked into ``text``, for sending with it."""
        return references(text, self._picked)

    def key(self, _controller, keyval, _code, _state) -> bool:
        if not self.popover.get_visible():
            return False
        if keyval in MOVES:
            self._move(MOVES[keyval])
            return True
        if keyval in COMPLETES:
            self._complete(self.list.get_selected_row().entry)
            return True
        if keyval == Gdk.KEY_Escape:
            self.popover.popdown()
            return True
        return False

    def _move(self, step: int) -> None:
        row = self.list.get_selected_row()
        rows = len(list(self.list))
        self.list.select_row(self.list.get_row_at_index(
            min(max(row.get_index() + step, 0), rows - 1)))

    def _complete(self, entry: Entry) -> None:
        buffer = self._entry.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        cursor = buffer.get_property("cursor-position")
        found = trigger(text, cursor)
        if found is None:
            return
        start = buffer.get_iter_at_offset(found.start)
        buffer.delete(start, buffer.get_iter_at_offset(cursor))
        # Picked before it goes in: putting it in re-marks the tokens.
        self._picked.append(entry)
        buffer.insert(start, f"{SIGN[entry.kind]}{entry.label} ")
        self._entry.grab_focus()

    def _typed(self) -> None:
        buffer = self._entry.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        self._mark(buffer, text)
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

    def _mark(self, buffer: Gtk.TextBuffer, text: str) -> None:
        """Tokens are what would be sent as references, so an edited one
        stops looking like one the moment it stops being one."""
        buffer.remove_tag(self.token, buffer.get_start_iter(), buffer.get_end_iter())
        for found in self.references(text):
            buffer.apply_tag(self.token, buffer.get_iter_at_offset(found.start),
                             buffer.get_iter_at_offset(found.end))

    def _point_at(self, where: Gtk.TextIter) -> None:
        place = self._entry.get_iter_location(where)
        x, y = self._entry.buffer_to_window_coords(
            Gtk.TextWindowType.WIDGET, place.x, place.y)
        point = Gdk.Rectangle()
        point.x, point.y, point.width, point.height = x, y, 1, place.height
        self.popover.set_pointing_to(point)


def _row(entry: Entry) -> Gtk.ListBoxRow:
    line = Gtk.Box(spacing=10)
    label = Gtk.Label(label=entry.label, xalign=0, max_width_chars=28,
                      ellipsize=Pango.EllipsizeMode.START)
    label.add_css_class("harness-picker-label")
    line.append(label)
    if entry.description:
        about = Gtk.Label(label=entry.description, xalign=0, hexpand=True,
                          max_width_chars=1, ellipsize=Pango.EllipsizeMode.END)
        about.add_css_class("harness-meta")
        line.append(about)
    row = Gtk.ListBoxRow(child=line)
    row.entry = entry
    return row
