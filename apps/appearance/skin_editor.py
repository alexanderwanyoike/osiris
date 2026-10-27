"""The Skin editor: rename a Skin and choose its style, icons, cursor and font,
each shown as it would look."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Pango  # noqa: E402

THEMES_CHOICE = "Theme's choice"
AS_IT_IS = "As it is"
#: Icons that differ most between sets, so a row of them tells one from another.
SAMPLE_ICONS = ("folder", "user-home", "text-x-generic", "image-x-generic",
                "audio-x-generic", "user-trash")

CSS = b"""
.editor-card { padding: 8px; border-radius: 12px; }
flowboxchild:selected .editor-card { background: alpha(@accent_color, 0.18); }
flowboxchild:selected { background: none; }
.editor-heading { font-weight: 800; font-size: 1.05em; }
"""


@dataclass(frozen=True)
class Choice:
    label: str
    style: str | None
    icons: str | None
    cursor: str | None
    font: str | None


def _nothing() -> None:
    pass


def _heading(title: str, add: tuple[str, Callable[[], None]] | None) -> Gtk.Box:
    line = Gtk.Box(spacing=6)
    heading = Gtk.Label(label=title, xalign=0, hexpand=True)
    heading.add_css_class("editor-heading")
    line.append(heading)
    if add is not None:
        tooltip, clicked = add
        button = Gtk.Button(icon_name="list-add-symbolic", tooltip_text=tooltip)
        button.add_css_class("flat")
        button.connect("clicked", lambda _b: clicked())
        line.append(button)
    return line


def _section(title: str, add: tuple[str, Callable[[], None]] | None = None
             ) -> tuple[Gtk.Box, Gtk.FlowBox]:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    box.append(_heading(title, add))
    flow = Gtk.FlowBox(name=title, homogeneous=True, min_children_per_line=2,
                       max_children_per_line=4, column_spacing=8,
                       row_spacing=8, selection_mode=Gtk.SelectionMode.SINGLE)
    box.append(flow)
    return box, flow


def _card(label: str, preview: Gtk.Widget) -> Gtk.Box:
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    card.add_css_class("editor-card")
    card.append(preview)
    card.append(Gtk.Label(label=label, xalign=0, ellipsize=Pango.EllipsizeMode.END))
    return card


def _style_picture(picture: str | None) -> Gtk.Widget:
    if picture is None:
        return Gtk.Image(icon_name="preferences-desktop-appearance-symbolic",
                         pixel_size=40, height_request=130)
    shown = Gtk.Picture.new_for_filename(picture)
    shown.set_content_fit(Gtk.ContentFit.CONTAIN)
    shown.set_size_request(-1, 130)
    return shown


def _icon_row(theme_name: str | None) -> Gtk.Box:
    row = Gtk.Box(spacing=6, height_request=40)
    theme = Gtk.IconTheme()
    if theme_name is not None:
        theme.set_theme_name(theme_name)
    for icon in SAMPLE_ICONS:
        if theme_name is None:
            image = Gtk.Image(icon_name=icon, pixel_size=32)
        else:
            paintable = theme.lookup_icon(icon, None, 32, 1,
                                          Gtk.TextDirection.NONE, 0)
            image = Gtk.Image.new_from_paintable(paintable)
            image.set_pixel_size(32)
        row.append(image)
    return row


def _pointer_row(pictures: Sequence[str]) -> Gtk.Box:
    row = Gtk.Box(spacing=10, height_request=40)
    for path in pictures:
        picture = Gtk.Picture.new_for_filename(path)
        picture.set_size_request(32, 32)
        picture.set_can_shrink(False)
        row.append(picture)
    if not pictures:
        row.append(Gtk.Image(icon_name="input-mouse-symbolic", pixel_size=32))
    return row


class SkinEditor(Adw.Dialog):
    def __init__(self, label: str,
                 styles: Sequence[tuple[str, str, str | None]], style: str | None,
                 icon_sets: Sequence[str], icons: str | None,
                 cursor_sets: Sequence[str],
                 cursor_pictures: Mapping[str, Sequence[str]], cursor: str | None,
                 font: str | None, on_save: Callable[[Choice], bool | None],
                 on_code: Callable[[], None] = _nothing,
                 on_add_icons: Callable[[], None] = _nothing,
                 on_add_cursors: Callable[[], None] = _nothing,
                 on_add_fonts: Callable[[], None] = _nothing,
                 theme_icons: str | None = None, theme_font: str = "Sans 11"):
        super().__init__(title="Edit Skin", content_width=880,
                         content_height=760)
        self._on_save = on_save
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22,
                       margin_top=18, margin_bottom=18, margin_start=18,
                       margin_end=18)

        names = Adw.PreferencesGroup()
        self._name = Adw.EntryRow(title="Name", text=label)
        names.add(self._name)
        page.append(names)

        box, self._styles = _section("Style")
        self._style_names: list[str | None] = [name for name, _l, _p in styles]
        if style not in self._style_names:
            # A Skin whose style is unknown keeps its own sheets unless the
            # person picks another.
            self._style_names.insert(0, None)
            self._styles.append(_card(AS_IT_IS, _style_picture(None)))
        for name, shown, picture in styles:
            self._styles.append(_card(shown, _style_picture(picture)))
        self._pick(self._styles, self._style_names, style)
        page.append(box)

        box, self._icons = _section("Icons", ("Add an icon set", on_add_icons))
        self._icon_names: list[str | None] = [None, *icon_sets]
        if icons is not None and icons not in self._icon_names:
            self._icon_names.append(icons)
        for name in self._icon_names:
            self._icons.append(_card(name or THEMES_CHOICE,
                                     _icon_row(name or theme_icons)))
        self._pick(self._icons, self._icon_names, icons)
        page.append(box)

        box, self._cursors = _section("Cursor", ("Add a cursor set", on_add_cursors))
        self._cursor_names: list[str | None] = [None, *cursor_sets]
        if cursor is not None and cursor not in self._cursor_names:
            self._cursor_names.append(cursor)
        for name in self._cursor_names:
            pictures = cursor_pictures.get(name or "", [])
            self._cursors.append(_card(name or THEMES_CHOICE,
                                       _pointer_row(pictures)))
        self._pick(self._cursors, self._cursor_names, cursor)
        page.append(box)

        page.append(self._font_section(font, theme_font, on_add_fonts))

        code = Gtk.Button(label="Open in Code", halign=Gtk.Align.START)
        code.add_css_class("flat")
        code.connect("clicked", lambda _b: on_code())
        page.append(code)

        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                      vexpand=True)
        scroller.set_child(page)
        header = Adw.HeaderBar(show_end_title_buttons=False,
                               show_start_title_buttons=False)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda _b: self.close())
        header.pack_start(cancel)
        save = Gtk.Button(label="Save")
        save.add_css_class("suggested-action")
        save.connect("clicked", lambda _b: self._save())
        header.pack_end(save)
        toolbar = Adw.ToolbarView(content=scroller)
        toolbar.add_top_bar(header)
        self.set_child(toolbar)

    def _font_section(self, font: str | None, theme_font: str,
                      on_add: Callable[[], None]) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.append(_heading("Font", ("Add fonts", on_add)))
        line = Gtk.Box(spacing=12)
        self._keep_font = Gtk.CheckButton(label="Theme's font",
                                          active=font is None)
        self._font = Gtk.FontDialogButton(dialog=Gtk.FontDialog(),
                                          use_font=True, use_size=True)
        self._font.set_font_desc(Pango.FontDescription.from_string(
            font or theme_font))
        self._font.set_sensitive(font is not None)
        self._keep_font.connect(
            "toggled", lambda check: self._font.set_sensitive(not check.get_active()))
        line.append(self._keep_font)
        line.append(self._font)
        box.append(line)
        sample = Gtk.Label(label="The quick brown fox jumps over the lazy dog",
                           xalign=0)
        self._font.bind_property("font-desc", sample, "attributes", 0,
                                 lambda _binding, desc: _font_attributes(desc))
        sample.set_attributes(_font_attributes(self._font.get_font_desc()))
        box.append(sample)
        return box

    @staticmethod
    def _pick(flow: Gtk.FlowBox, names: Sequence[str | None],
              current: str | None) -> None:
        index = names.index(current) if current in names else 0
        child = flow.get_child_at_index(index)
        if child is not None:
            flow.select_child(child)

    @staticmethod
    def _selected(flow: Gtk.FlowBox, names: Sequence[str | None]) -> str | None:
        children = flow.get_selected_children()
        return names[children[0].get_index()] if children else None

    def _save(self) -> None:
        font = None if self._keep_font.get_active() else (
            self._font.get_font_desc().to_string())
        saved = self._on_save(Choice(
            label=self._name.get_text().strip(),
            style=self._selected(self._styles, self._style_names),
            icons=self._selected(self._icons, self._icon_names),
            cursor=self._selected(self._cursors, self._cursor_names),
            font=font,
        ))
        if saved is not False:
            self.close()


def _font_attributes(desc: Pango.FontDescription | None) -> Pango.AttrList:
    attributes = Pango.AttrList()
    if desc is not None:
        attributes.insert(Pango.attr_font_desc_new(desc))
    return attributes
