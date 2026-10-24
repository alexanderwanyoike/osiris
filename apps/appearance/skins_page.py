"""Appearance's Skins section: every Skin, the chosen one marked, one click to wear."""

from collections.abc import Callable, Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

#: (name, label, who made it)
Skin = tuple[str, str, str]


class SkinsPage(Adw.PreferencesPage):
    def __init__(self, skins: Sequence[Skin], chosen: str,
                 on_pick: Callable[[str], None]):
        super().__init__()
        group = Adw.PreferencesGroup(
            title="Skins",
            description="The shape of everything on the desktop: windows, "
                        "panel, dock, fonts and icons. Your Theme gives it "
                        "its colours.")
        for name, label, credit in skins:
            row = Adw.ActionRow(title=label, subtitle=credit, activatable=True)
            mark = Gtk.Image(icon_name="object-select-symbolic",
                             visible=name == chosen)
            row.add_suffix(mark)
            row.connect("activated", lambda _row, skin=name: on_pick(skin))
            group.add(row)
        self.add(group)
