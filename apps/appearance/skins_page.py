"""Appearance's Skins section: every Skin as a card with a picture of it, the
chosen one marked, one click to wear."""

from collections.abc import Callable, Mapping, Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

#: (name, label, who made it)
Skin = tuple[str, str, str]

OSIRIS = "osiris"

CSS = b"""
.skin-card { border-radius: 14px; padding: 8px; border: 2px solid transparent; }
.skin-card.selected { border-color: @accent_color; }
.skin-card picture, .skin-card .skin-blank { border-radius: 10px; }
.skin-blank { background: alpha(currentColor, 0.06); }
.skin-name { font-weight: 700; }
"""


def _nothing(*_args) -> None:
    pass


def _button(icon: str, tooltip: str, clicked: Callable[[], None]) -> Gtk.Button:
    button = Gtk.Button(icon_name=icon, tooltip_text=tooltip,
                        valign=Gtk.Align.CENTER)
    button.add_css_class("flat")
    button.connect("clicked", lambda _b: clicked())
    return button


def _picture(preview: str | None) -> Gtk.Widget:
    if preview is None:
        blank = Gtk.Image(icon_name="preferences-desktop-appearance-symbolic",
                          pixel_size=48, height_request=170)
        blank.add_css_class("skin-blank")
        blank.add_css_class("dim-label")
        return blank
    picture = Gtk.Picture.new_for_filename(preview)
    picture.set_content_fit(Gtk.ContentFit.COVER)
    picture.set_size_request(280, 170)
    return picture


class SkinsPage(Adw.PreferencesPage):
    def __init__(self, skins: Sequence[Skin], chosen: str,
                 on_pick: Callable[[str], None],
                 mine: frozenset[str] | set[str] = frozenset(),
                 previews: Mapping[str, str] | None = None,
                 on_open: Callable[[], None] = _nothing,
                 on_export: Callable[[str], None] = _nothing,
                 on_delete: Callable[[str], None] = _nothing,
                 on_duplicate: Callable[[str], None] = _nothing,
                 on_change: Callable[[str], None] = _nothing,
                 on_edit: Callable[[str], None] = _nothing,
                 on_create: Callable[[], None] = _nothing):
        super().__init__()
        previews = previews or {}
        group = Adw.PreferencesGroup(
            title="Skins",
            description="The shape of everything on the desktop: windows, "
                        "panel, dock, fonts and icons. Your Theme gives it "
                        "its colours.")
        flow = Gtk.FlowBox(homogeneous=True, min_children_per_line=2,
                           max_children_per_line=3, column_spacing=12,
                           row_spacing=12,
                           selection_mode=Gtk.SelectionMode.NONE)
        names = [name for name, _label, _credit in skins]
        flow.connect("child-activated",
                     lambda _flow, child: on_pick(names[child.get_index()]))
        for name, label, credit in skins:
            buttons = Gtk.Box(spacing=0)
            if name in mine:
                buttons.append(_button("osiris-ask-symbolic",
                                       "Ask Osiris to change it",
                                       lambda skin=name: on_change(skin)))
                buttons.append(_button("document-edit-symbolic", "Edit",
                                       lambda skin=name: on_edit(skin)))
                buttons.append(_button("user-trash-symbolic", "Delete",
                                       lambda skin=name: on_delete(skin)))
            if name != OSIRIS:
                buttons.append(_button("edit-copy-symbolic", "Duplicate",
                                       lambda skin=name: on_duplicate(skin)))
                buttons.append(_button("document-save-symbolic", "Export",
                                       lambda skin=name: on_export(skin)))
            flow.append(self._card(name == chosen, label, credit,
                                   previews.get(name), buttons))
        group.add(flow)
        header = Gtk.Box(spacing=6)
        header.append(_button("list-add-symbolic", "New Skin", on_create))
        header.append(_button("document-open-symbolic", "Open a skinpack",
                              on_open))
        group.set_header_suffix(header)
        self.add(group)

    @staticmethod
    def _card(chosen: bool, label: str, credit: str, preview: str | None,
              buttons: Gtk.Box) -> Gtk.Box:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.add_css_class("skin-card")
        if chosen:
            card.add_css_class("selected")
        card.append(_picture(preview))
        line = Gtk.Box(spacing=6)
        words = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        title = Gtk.Label(label=label, xalign=0)
        title.add_css_class("skin-name")
        maker = Gtk.Label(label=credit, xalign=0, ellipsize=3)
        maker.add_css_class("dim-label")
        maker.add_css_class("caption")
        words.append(title)
        words.append(maker)
        line.append(words)
        line.append(Gtk.Image(icon_name="object-select-symbolic", visible=chosen))
        card.append(line)
        card.append(buttons)
        return card
