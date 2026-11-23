"""The Media section of Settings: FAL, connected by a key of the person's."""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from badge import badge  # noqa: E402
from provider_parts import add_key, connected_chip  # noqa: E402


class MediaSection(Gtk.Box):
    def __init__(self, connected: Callable[[], bool], save: Callable[[str], None],
                 remove: Callable[[], None]) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._connected = connected
        self._save = save
        self._remove = remove
        self.append(Gtk.Label(label="Media", xalign=0))
        self._card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._card.add_css_class("harness-provider-card")
        self.append(self._card)
        self._draw()

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
