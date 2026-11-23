"""The Media section of Settings: FAL, connected by a key of the person's."""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from badge import badge  # noqa: E402
from provider_parts import add_key  # noqa: E402


class MediaSection(Gtk.Box):
    def __init__(self, connected: Callable[[], bool], save: Callable[[str], None],
                 remove: Callable[[], None]) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._connected = connected
        self._save = save
        self._remove = remove
        self.append(Gtk.Label(label="Media", xalign=0))
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.add_css_class("harness-provider-card")
        row = Gtk.Box(spacing=10)
        row.add_css_class("harness-provider")
        row.append(badge(None, "FAL", 20))
        row.append(Gtk.Label(label="FAL", xalign=0, hexpand=True))
        card.append(row)
        add_key(card, save)
        self.append(card)
