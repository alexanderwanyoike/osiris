"""The / and @ picker on the message box (#153).

What opens it, what it lists and where picked entries stand in the text are
decided in osiris/harness/picker.py; this draws the list as a card over the
message box and puts the chosen entry into the message.
"""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Graphene, Gtk, Pango  # noqa: E402

from osiris.harness.picker import (  # noqa: E402
    SIGN,
    Entry,
    Reference,
    matching,
    references,
    trigger,
)

#: Rows listed at most, so a Project of thousands of files stays quick to
#: filter; typing narrows the rest.
LISTED = 200
#: The card's tallest, about ten rows; the rest scroll.
HEIGHT = 300
ROWS = 10
#: Space between the card and the message box under it.
GAP = 8
ICONS = {
    "file": "text-x-generic-symbolic",
    "skill": "applications-science-symbolic",
    "command": "system-run-symbolic",
}
MOVES = {Gdk.KEY_Down: 1, Gdk.KEY_Up: -1}
COMPLETES = (Gdk.KEY_Tab, Gdk.KEY_Return, Gdk.KEY_KP_Enter)


class Picker:
    def __init__(self, entry: Gtk.TextView, offered: Callable[[str], list[Entry]],
                 anchor: Gtk.Widget | None = None,
                 on_open: Callable[[str], None] = lambda _sign: None):
        self._entry = entry
        #: Told the sign each time the picker opens, to fetch afresh what it
        #: lists; an Engine still starting up can offer less at first.
        self._on_open = on_open
        #: What the card sits over, at its full width: the whole message box.
        self._anchor = anchor or entry
        self._offered = offered
        self._picked: list[Entry] = []
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.BROWSE)
        self.list.add_css_class("harness-picker")
        self.list.connect("row-activated", lambda _l, row: self._complete(row.entry))
        # The chosen row follows the pointer, so only one row is ever lit.
        pointer = Gtk.EventControllerMotion()
        pointer.connect("motion", self.pointed)
        self.list.add_controller(pointer)
        # Without autohide the popover leaves the keyboard with the message
        # box, so typing carries on filtering while it is open.
        self.card = Gtk.ScrolledWindow(child=self.list, max_content_height=HEIGHT,
                                       propagate_natural_height=True,
                                       hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.popover = Gtk.Popover(child=self.card, autohide=False, has_arrow=False,
                                   position=Gtk.PositionType.TOP)
        self.popover.add_css_class("harness-picker-popover")
        self.popover.set_offset(0, -GAP)
        self.popover.set_parent(self._anchor)
        self.token = entry.get_buffer().create_tag("harness-token", weight=500)
        entry.get_buffer().connect("changed", lambda _b: self._typed())
        # Captured before the message box sees them, so Enter picks an entry
        # rather than sending while the picker is open.
        keys = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self.key)
        entry.add_controller(keys)

    def refresh(self) -> None:
        """What it lists has changed; an open picker lists it again."""
        if self.popover.get_visible():
            self._typed()

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

    def pointed(self, _controller, _x: float, y: float) -> None:
        row = self.list.get_row_at_y(int(y))
        if row is not None and row is not self.list.get_selected_row():
            self.list.select_row(row)

    def _move(self, step: int) -> None:
        row = self.list.get_selected_row()
        rows = len(list(self.list))
        chosen = self.list.get_row_at_index(min(max(row.get_index() + step, 0), rows - 1))
        self.list.select_row(chosen)
        self._reveal(chosen)

    def _reveal(self, row: Gtk.ListBoxRow) -> None:
        _found, at = row.compute_point(self.list, Graphene.Point())
        shown = self.card.get_vadjustment()
        top, page = shown.get_value(), shown.get_page_size()
        if at.y < top:
            shown.set_value(at.y)
        elif at.y + row.get_height() > top + page:
            shown.set_value(at.y + row.get_height() - page)

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
        if not self.popover.get_visible():
            self._on_open(found.sign)
        self.list.remove_all()
        for entry in entries[:LISTED]:
            self.list.append(_row(entry))
        # A scrollbar has a least length that would hold a short card open
        # below its rows, so there is one only when there is more to see.
        self.card.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC
                             if len(entries) > ROWS else Gtk.PolicyType.NEVER)
        self.list.select_row(self.list.get_row_at_index(0))
        # The anchor's width, whatever is listed, so the card holds still
        # while typing narrows it; descriptions are cut to fit. Its bounds,
        # not get_width(), which leaves out its padding.
        _found, edges = self._anchor.compute_bounds(self._anchor)
        self.list.set_size_request(round(edges.get_width()), -1)
        self.popover.popup()

    def _mark(self, buffer: Gtk.TextBuffer, text: str) -> None:
        """Tokens are what would be sent as references, so an edited one
        stops looking like one the moment it stops being one."""
        buffer.remove_tag(self.token, buffer.get_start_iter(), buffer.get_end_iter())
        for found in self.references(text):
            buffer.apply_tag(self.token, buffer.get_iter_at_offset(found.start),
                             buffer.get_iter_at_offset(found.end))


def _row(entry: Entry) -> Gtk.ListBoxRow:
    line = Gtk.Box(spacing=10)
    icon = Gtk.Image(icon_name=ICONS[entry.kind])
    icon.add_css_class("harness-picker-icon")
    line.append(icon)
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
