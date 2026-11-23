"""The Media section of Settings: FAL, connected by a key of the person's."""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from badge import badge  # noqa: E402
from provider_parts import add_key, connected_chip  # noqa: E402

from osiris.harness.media.limit_setting import SUGGESTED_LIMIT  # noqa: E402


class MediaSection(Gtk.Box):
    def __init__(self, connected: Callable[[], bool], save: Callable[[str], None],
                 remove: Callable[[], None], limit: Callable[[], int | None],
                 set_limit: Callable[[int | None], None]) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._connected = connected
        self._save = save
        self._remove = remove
        self._limit = limit
        self._set_limit = set_limit
        self.append(Gtk.Label(label="Media", xalign=0))
        purpose = Gtk.Label(
            label="Makes pictures for Themes on your FAL account.",
            xalign=0, wrap=True)
        purpose.add_css_class("harness-meta")
        self.append(purpose)
        self._card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._card.add_css_class("harness-provider-card")
        self.append(self._card)
        self.append(self._limit_row())
        self._draw()

    def _limit_row(self) -> Gtk.Widget:
        chosen = self._limit()
        self._amount = Gtk.SpinButton.new_with_range(1, 1000, 1)
        self._amount.set_value(SUGGESTED_LIMIT if chosen is None else chosen)
        self._amount.set_visible(chosen is not None)
        switch = Gtk.Switch(active=chosen is not None, valign=Gtk.Align.CENTER)
        switch.connect("notify::active", self._limit_switched)
        line = Gtk.Box(spacing=8)
        line.append(Gtk.Label(label="Daily picture limit", xalign=0, hexpand=True))
        line.append(self._amount)
        line.append(switch)
        return line

    def _limit_switched(self, switch: Gtk.Switch, _spec: object) -> None:
        on = switch.get_active()
        self._amount.set_visible(on)
        self._set_limit(self._amount.get_value_as_int() if on else None)

    def _draw(self) -> None:
        while (child := self._card.get_first_child()) is not None:
            self._card.remove(child)
        row = Gtk.Box(spacing=10)
        row.add_css_class("harness-provider")
        row.append(badge(None, "FAL", 20))
        row.append(Gtk.Label(label="FAL", xalign=0, hexpand=True))
        self._card.append(row)
        if self._connected():
            row.append(connected_chip())
            remove = Gtk.Button(label="Remove key", halign=Gtk.Align.START)
            remove.add_css_class("flat")
            remove.connect("clicked", self._removed)
            self._card.append(remove)
        else:
            add_key(self._card, self._saved)

    def _saved(self, key: str) -> None:
        if not key:
            return
        self._save(key)
        self._draw()

    def _removed(self, _button: Gtk.Button) -> None:
        self._remove()
        self._draw()
