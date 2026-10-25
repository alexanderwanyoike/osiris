"""Appearance's Skins section: every Skin, the chosen one marked, one click to wear."""

from collections.abc import Callable, Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

#: (name, label, who made it)
Skin = tuple[str, str, str]


OSIRIS = "osiris"


def _nothing(*_args) -> None:
    pass


def _button(icon: str, tooltip: str, clicked: Callable[[], None]) -> Gtk.Button:
    button = Gtk.Button(icon_name=icon, tooltip_text=tooltip,
                        valign=Gtk.Align.CENTER)
    button.add_css_class("flat")
    button.connect("clicked", lambda _b: clicked())
    return button


class SkinsPage(Adw.PreferencesPage):
    def __init__(self, skins: Sequence[Skin], chosen: str,
                 on_pick: Callable[[str], None], mine: frozenset[str] | set[str] = frozenset(),
                 on_open: Callable[[], None] = _nothing,
                 on_export: Callable[[str], None] = _nothing,
                 on_delete: Callable[[str], None] = _nothing,
                 on_duplicate: Callable[[str], None] = _nothing,
                 on_change: Callable[[str], None] = _nothing):
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
            if name in mine:
                row.add_suffix(_button("document-edit-symbolic",
                                       "Ask Osiris to change it",
                                       lambda skin=name: on_change(skin)))
                row.add_suffix(_button("user-trash-symbolic", "Delete",
                                       lambda skin=name: on_delete(skin)))
            if name != OSIRIS:
                row.add_suffix(_button("edit-copy-symbolic", "Duplicate",
                                       lambda skin=name: on_duplicate(skin)))
                row.add_suffix(_button("document-save-symbolic", "Export",
                                       lambda skin=name: on_export(skin)))
            row.add_suffix(mark)
            row.connect("activated", lambda _row, skin=name: on_pick(skin))
            group.add(row)
        group.set_header_suffix(_button("document-open-symbolic",
                                        "Open a skinpack", on_open))
        self.add(group)
