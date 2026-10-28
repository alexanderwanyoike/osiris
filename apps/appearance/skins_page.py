"""Appearance's Skins section: every Skin as a card with a picture of it, the
chosen one marked, one click to wear."""

from collections.abc import Callable, Mapping, Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Pango  # noqa: E402

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
                          pixel_size=48, height_request=230)
        blank.add_css_class("skin-blank")
        blank.add_css_class("dim-label")
        return blank
    picture = Gtk.Picture.new_for_filename(preview)
    picture.set_content_fit(Gtk.ContentFit.CONTAIN)
    picture.set_size_request(-1, 230)
    return picture


class SkinsPage(Gtk.ScrolledWindow):
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
                 on_create: Callable[[], None] = _nothing,
                 on_import: Callable[[], None] = _nothing):
        super().__init__(hscrollbar_policy=Gtk.PolicyType.NEVER)
        previews = previews or {}
        self._pictures: dict[str, Gtk.Widget] = {}
        flow = Gtk.FlowBox(homogeneous=True, min_children_per_line=3,
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
            self._pictures[name] = _picture(previews.get(name))
            flow.append(self._card(name == chosen, label, credit,
                                   self._pictures[name], buttons))
        heading = Gtk.Box(spacing=6)
        words = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                        spacing=4)
        title = Gtk.Label(label="Skins", xalign=0)
        title.add_css_class("title-4")
        about = Gtk.Label(
            label="The shape of everything on the desktop: windows, panel, "
                  "dock, fonts and icons. Your Theme gives it its colours.",
            xalign=0, wrap=True)
        about.add_css_class("dim-label")
        words.append(title)
        words.append(about)
        heading.append(words)
        heading.append(_button("list-add-symbolic", "New Skin", on_create))
        heading.append(_button("document-open-symbolic", "Open a skinpack",
                               on_open))
        heading.append(_button("folder-download-symbolic", "Import a GTK theme",
                               on_import))
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                       margin_top=18, margin_bottom=18, margin_start=18,
                       margin_end=18)
        page.append(heading)
        page.append(flow)
        self.set_child(Adw.Clamp(child=page, maximum_size=1280,
                                 tightening_threshold=1000))

    def show_picture(self, name: str, preview: str) -> None:
        """Put a picture drawn since on its card, leaving the rest as it is."""
        old = self._pictures.get(name)
        card = old.get_parent() if old is not None else None
        if card is None:
            return
        self._pictures[name] = _picture(preview)
        card.insert_child_after(self._pictures[name], old)
        card.remove(old)

    @staticmethod
    def _card(chosen: bool, label: str, credit: str, picture: Gtk.Widget,
              buttons: Gtk.Box) -> Gtk.Box:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.add_css_class("skin-card")
        if chosen:
            card.add_css_class("selected")
        card.append(picture)
        line = Gtk.Box(spacing=6)
        words = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        title = Gtk.Label(label=label, xalign=0)
        title.add_css_class("skin-name")
        maker = Gtk.Label(label=credit, xalign=0,
                          ellipsize=Pango.EllipsizeMode.END)
        maker.add_css_class("dim-label")
        maker.add_css_class("caption")
        words.append(title)
        words.append(maker)
        line.append(words)
        line.append(Gtk.Image(icon_name="object-select-symbolic", visible=chosen))
        card.append(line)
        card.append(buttons)
        return card


def new_skin(bases: Sequence[Skin],
             on_create: Callable[[str, str], None]) -> Adw.AlertDialog:
    """Ask for a new Skin's name and the Skin it starts from."""
    name = Gtk.Entry(placeholder_text="Name", activates_default=True)
    base = Gtk.DropDown.new_from_strings([label for _n, label, _c in bases])
    form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    form.append(name)
    form.append(Gtk.Label(label="Start from", xalign=0))
    form.append(base)
    dialog = Adw.AlertDialog(
        heading="New Skin",
        body="Name it and pick a Skin to start from; then tell Osiris "
             "how it should look.",
        extra_child=form)
    dialog.add_response("cancel", "Cancel")
    dialog.add_response("create", "Create")
    dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("create")

    def named(_entry=None) -> None:
        dialog.set_response_enabled(
            "create", bool(bases) and bool(name.get_text().strip()))

    def answered(_dialog, response: str) -> None:
        if response == "create":
            on_create(name.get_text().strip(), bases[base.get_selected()][0])

    name.connect("changed", named)
    named()
    dialog.connect("response", answered)
    return dialog
