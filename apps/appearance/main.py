#!/usr/bin/env python3
"""Osiris Appearance - pick a theme from live previews.

GTK4 + libadwaita. Each theme is a card showing a rendered miniature of the
desktop in that palette; clicking one applies it immediately. With many themes
the window stays navigable: search as you type, filter to dark, light or your
own, star favourites, and themes are grouped by the colour family of their
accent (osiris/themes/library.py).

Run directly, or install the .desktop file alongside it.
"""
import os
import sys
import threading
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import (  # noqa: E402
    Adw, Gdk, GdkPixbuf, Gio, GLib, GObject, Gtk)

# /usr/bin/osiris-appearance runs this through runpy, which does not put the
# script's own directory on the path the way running it directly does.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The theme engine lives with the themes; find it whether running from the
# repo or from /usr/share/osiris.
for candidate in (
    os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), "shell", "themes"),
    "/usr/share/osiris/themes",
):
    if os.path.isdir(candidate):
        sys.path.insert(0, candidate)
        break

import drift  # noqa: E402
import engine  # noqa: E402

from creator import Creator  # noqa: E402
from skin_editor import CSS as EDITOR_CSS, SkinEditor  # noqa: E402
from skins_page import CSS as SKINS_CSS, SkinsPage, new_skin  # noqa: E402

# creator has put the osiris package on sys.path.
from osiris.apps.theme_scheme import ThemeScheme  # noqa: E402
from osiris.apps.user_css import UserCss  # noqa: E402
from osiris.model.names import slug  # noqa: E402
from osiris.skins.imports import ARCHIVE_SUFFIXES, FONT_SUFFIXES  # noqa: E402
from osiris.themes.library import Filter, arrange  # noqa: E402

ARCHIVES = ARCHIVE_SUFFIXES
FONTS = tuple(sorted(FONT_SUFFIXES))
CONVERT = ("Convert this imported theme so it follows my Theme: replace its "
           "written-in colours with the Theme's gaps, for light and dark, then "
           "wear it.")
HARNESS = "dev.osiris.Harness"
HARNESS_PATH = "/dev/osiris/Harness"
#: Long enough for D-Bus to start Osiris cold and for it to answer.
HARNESS_START_MS = 60_000

FILTERS = ((Filter.ALL, "All"), (Filter.DARK, "Dark"),
           (Filter.LIGHT, "Light"), (Filter.MINE, "Mine"))

CSS = b"""
.theme-card {
    padding: 0;
    border-radius: 14px;
    background: transparent;
    border: 2px solid transparent;
    transition: background 120ms ease;
}
.theme-card:hover { background: alpha(currentColor, 0.05); }
.theme-card.selected { border-color: @accent_color; }
.theme-name { font-weight: 700; }
.variant-badge {
    font-size: 0.78em;
    padding: 1px 8px;
    border-radius: 999px;
    background: alpha(currentColor, 0.12);
}
.card-menu, .card-star {
    opacity: 0;
    min-width: 28px;
    min-height: 28px;
    padding: 0;
    border-radius: 999px;
    transition: opacity 120ms ease;
}
.card-star { background: alpha(black, 0.35); color: white; }
.card-star.starred { opacity: 1; color: #f6c544; }
overlay:hover .card-menu,
overlay:hover .card-star,
.card-menu:focus-within,
.card-menu:checked { opacity: 1; }
.section-title { font-weight: 800; font-size: 1.05em; }
.section-count { opacity: 0.55; }
.filters { margin: 6px 18px 0 18px; }
"""


class Preview(Gtk.DrawingArea):
    """A theme's preview image, cropped to fill and rounded.

    A Gtk.Picture asks for its image's full size, so a grid of them lays out
    two to a row whatever the window's width; this asks for a card's size and
    draws the image scaled to cover whatever it is given.
    """

    RADIUS = 10

    def __init__(self, path: str | None):
        super().__init__(content_width=232, content_height=145)
        self.image = None
        if path and os.path.exists(path):
            try:
                self.image = GdkPixbuf.Pixbuf.new_from_file(path)
            except GLib.Error:
                self.image = None
        self.set_draw_func(self._draw)

    def _draw(self, _area, cr, width: int, height: int) -> None:
        r = self.RADIUS
        cr.new_sub_path()
        cr.arc(width - r, r, r, -1.5708, 0)
        cr.arc(width - r, height - r, r, 0, 1.5708)
        cr.arc(r, height - r, r, 1.5708, 3.14159)
        cr.arc(r, r, r, 3.14159, 4.71239)
        cr.close_path()
        cr.clip()
        if self.image is None:
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.15)
            cr.paint()
            return
        scale = max(width / self.image.get_width(),
                    height / self.image.get_height())
        cr.translate((width - self.image.get_width() * scale) / 2,
                     (height - self.image.get_height() * scale) / 2)
        cr.scale(scale, scale)
        Gdk.cairo_set_source_pixbuf(cr, self.image, 0, 0)
        cr.paint()


class ThemeCard(Gtk.Overlay):
    """A clickable theme card with a star and a menu button over it.

    An Overlay wrapping a Button, rather than a Button containing the rest. A
    GtkButton takes the pointer across its whole area, so a button nested
    inside one is visible, highlights on hover, and never fires. Overlay
    children sit above the main child and are offered input first, which gives
    the card one large hit target and its small buttons their own.
    """

    def __init__(self, theme: dict, on_pick, starred: bool, on_star):
        super().__init__()
        self.theme = theme

        self.button = Gtk.Button()
        self.button.add_css_class("theme-card")
        self.button.add_css_class("flat")
        self.button.connect("clicked", lambda _b: on_pick(theme))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for side in ("top", "bottom", "start", "end"):
            getattr(box, f"set_margin_{side}")(7)

        box.append(Preview(theme.get("preview")))

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name = Gtk.Label(label=theme["label"], xalign=0,
                         ellipsize=3)                 # Pango.EllipsizeMode.END
        name.add_css_class("theme-name")
        name.set_hexpand(True)
        row.append(name)
        badge = Gtk.Label(label="Dark" if theme.get("dark", True) else "Light")
        badge.add_css_class("variant-badge")
        row.append(badge)
        # Room for the overlaid menu button, which would otherwise cover this.
        row.set_margin_end(32)
        box.append(row)

        self.button.set_child(box)
        self.set_child(self.button)
        self.add_overlay(self._star(theme, starred, on_star))
        self.add_overlay(self._menu(theme))

    def _star(self, theme: dict, starred: bool, on_star) -> Gtk.ToggleButton:
        star = Gtk.ToggleButton(active=starred,
                                tooltip_text="Favourite")
        star.set_icon_name("starred-symbolic" if starred
                           else "non-starred-symbolic")
        star.set_halign(Gtk.Align.END)
        star.set_valign(Gtk.Align.START)
        star.set_margin_top(14)
        star.set_margin_end(14)
        star.add_css_class("card-star")
        if starred:
            star.add_css_class("starred")
        star.connect("toggled",
                     lambda b: on_star(theme["name"], b.get_active()))
        return star

    def _menu(self, theme: dict) -> Gtk.MenuButton:
        """Per-card actions.

        A shipped theme can only be duplicated - its file is root-owned, and an
        edit would be lost on the next package update anyway. Forking it into
        the user's directory is the supported way to change one.
        """
        menu = Gio.Menu()
        menu.append("Duplicate", f"win.duplicate::{theme['name']}")
        if engine.is_user_theme(theme["name"]):
            menu.append("Edit", f"win.edit::{theme['name']}")
            menu.append("Delete", f"win.delete::{theme['name']}")

        button = Gtk.MenuButton(icon_name="view-more-symbolic")
        button.set_menu_model(menu)
        button.set_halign(Gtk.Align.END)
        button.set_valign(Gtk.Align.END)
        button.set_margin_end(10)
        button.set_margin_bottom(6)
        button.add_css_class("flat")
        button.add_css_class("card-menu")
        return button

    def set_selected(self, selected: bool) -> None:
        if selected:
            self.button.add_css_class("selected")
        else:
            self.button.remove_css_class("selected")


class Window(Adw.ApplicationWindow):
    def _drift_toggled(self, button) -> None:
        drift.set_enabled(button.get_active())

    def _explain_drift(self) -> bool:
        """Say why the wallpaper is not moving, once per reason.

        Asked every few seconds: drift.py checks a shader after a theme is
        applied, and the extension finds out about the GPU while it draws.
        """
        problem = drift.problem() if drift.enabled() else None
        self.drift.set_tooltip_text(problem or "Let generated wallpapers move")
        if problem:
            self.drift.add_css_class("warning")
        else:
            self.drift.remove_css_class("warning")
        if problem and problem != self.explained:
            self.toasts.add_toast(Adw.Toast(
                title=problem.splitlines()[0], timeout=8))
        self.explained = problem
        return GLib.SOURCE_CONTINUE

    def __init__(self, app):
        super().__init__(application=app, title="Appearance")
        self.set_default_size(1080, 760)
        self.cards: list[ThemeCard] = []
        self.themes: list[dict] = []
        self.chosen = Filter.ALL

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.views = Adw.ViewStack()
        header.set_title_widget(Adw.ViewSwitcher(
            stack=self.views, policy=Adw.ViewSwitcherPolicy.WIDE))
        new_button = Gtk.Button(icon_name="list-add-symbolic",
                                tooltip_text="New theme")
        new_button.connect("clicked", lambda _b: self.create())
        header.pack_start(new_button)
        self.drift = Gtk.ToggleButton(
            label="Drift", active=drift.enabled(),
            tooltip_text="Let generated wallpapers move")
        self.drift.connect("toggled", self._drift_toggled)
        header.pack_end(self.drift)
        self.explained: str | None = None
        search_button = Gtk.ToggleButton(icon_name="system-search-symbolic",
                                         tooltip_text="Search themes")
        header.pack_end(search_button)
        toolbar.add_top_bar(header)

        self.search = Gtk.SearchEntry(placeholder_text="Search themes")
        self.search.connect("search-changed", lambda *_a: self.refresh())
        search_bar = Gtk.SearchBar(child=Adw.Clamp(child=self.search,
                                                   maximum_size=520))
        search_bar.connect_entry(self.search)
        # Typing anywhere in the window starts a search.
        search_bar.set_key_capture_widget(self)
        search_button.bind_property(
            "active", search_bar, "search-mode-enabled",
            GObject.BindingFlags.BIDIRECTIONAL)
        toolbar.add_top_bar(search_bar)

        filters = Gtk.Box(spacing=12)
        filters.add_css_class("filters")
        chips = Gtk.Box()
        chips.add_css_class("linked")
        first = None
        for chosen, label in FILTERS:
            chip = Gtk.ToggleButton(label=label, active=chosen is Filter.ALL)
            if first is None:
                first = chip
            else:
                chip.set_group(first)
            chip.connect("toggled", self._filter_toggled, chosen)
            chips.append(chip)
        filters.append(chips)
        filters.append(Gtk.Box(hexpand=True))
        self.count = Gtk.Label()
        self.count.add_css_class("dim-label")
        filters.append(self.count)
        toolbar.add_top_bar(filters)

        # One parameterised action per menu entry, with the theme name as the
        # target, rather than a closure per card: the cards are rebuilt on
        # every change and the actions outlive them.
        for name, handler in (("duplicate", self.duplicate),
                              ("edit", self.edit),
                              ("delete", self.confirm_delete)):
            action = Gio.SimpleAction.new(name, GLib.VariantType.new("s"))
            action.connect("activate",
                           lambda _a, target, fn=handler: fn(target.get_string()))
            self.add_action(action)

        self.toasts = Adw.ToastOverlay()
        self.sections = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                spacing=26)
        for side in ("top", "bottom", "start", "end"):
            getattr(self.sections, f"set_margin_{side}")(18)
        self.empty = Adw.StatusPage(icon_name="system-search-symbolic",
                                    title="No themes match",
                                    description="Try another name or filter")
        self.stack = Gtk.Stack()
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(Adw.Clamp(child=self.sections, maximum_size=1280,
                                     tightening_threshold=1000))
        self.stack.add_named(scroller, "themes")
        self.stack.add_named(self.empty, "empty")
        self.stack.set_vexpand(True)

        self.views.add_titled_with_icon(self.stack, "themes", "Themes",
                                        "applications-graphics-symbolic")
        self.skins = Adw.Bin()
        self.views.add_titled_with_icon(self.skins, "skins", "Skins",
                                        "preferences-desktop-appearance-symbolic")
        # Search, filters and New belong to Themes.
        for themes_only in (new_button, search_button, search_bar, filters):
            self.views.bind_property(
                "visible-child-name", themes_only, "visible",
                GObject.BindingFlags.SYNC_CREATE,
                lambda _binding, page: page == "themes")
        self.toasts.set_child(self.views)
        self._show_skins()
        toolbar.set_content(self.toasts)
        self.set_content(toolbar)
        self.reload()
        self._explain_drift()
        GLib.timeout_add_seconds(5, self._explain_drift)

    def _filter_toggled(self, chip, chosen: Filter) -> None:
        if chip.get_active():
            self.chosen = chosen
            self.refresh()

    def _starred(self, name: str, starred: bool) -> None:
        engine.set_favourite(name, starred)
        # Rebuilt after the click has finished: removing the card that is
        # handling it, inside its own handler, is asking for trouble.
        GLib.idle_add(lambda: self.refresh() and False)

    def reload(self) -> None:
        """Read the themes from disk, then show them."""
        self.themes = engine.all_themes()
        self.refresh()

    def refresh(self) -> None:
        """Show the themes matching the search and filter, in sections."""
        while (child := self.sections.get_first_child()) is not None:
            self.sections.remove(child)
        self.cards = []
        active = engine.current()
        starred = engine.favourites()
        mine = {t["name"] for t in self.themes if engine.is_user_theme(t["name"])}
        arranged = arrange(self.themes, query=self.search.get_text(),
                           chosen=self.chosen, favourites=starred, mine=mine)
        shown = sum(len(members) for _title, members in arranged)
        self.count.set_label(f"{shown} theme{'s' if shown != 1 else ''}")
        self.stack.set_visible_child_name("themes" if arranged else "empty")
        for title, members in arranged:
            section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            heading = Gtk.Box(spacing=8)
            label = Gtk.Label(label=title, xalign=0)
            label.add_css_class("section-title")
            heading.append(label)
            count = Gtk.Label(label=str(len(members)))
            count.add_css_class("section-count")
            heading.append(count)
            section.append(heading)
            flow = Gtk.FlowBox(valign=Gtk.Align.START, homogeneous=True,
                               max_children_per_line=5, min_children_per_line=2,
                               selection_mode=Gtk.SelectionMode.NONE,
                               row_spacing=8, column_spacing=8)
            for theme in members:
                card = ThemeCard(theme, self.pick, theme["name"] in starred,
                                 self._starred)
                card.set_selected(theme["name"] == active)
                self.cards.append(card)
                flow.append(card)
            section.append(flow)
            self.sections.append(section)

    # --------------------------------------------------------------- actions

    def create(self, source: dict | None = None, editing: bool = False) -> None:
        Creator(self, self.saved, source=source, editing=editing).present(self)

    def saved(self, name: str) -> None:
        self.reload()
        try:
            self.pick(engine.load(name))
        except (KeyError, OSError, ValueError) as error:
            self.toasts.add_toast(Adw.Toast(title=f"Saved, but could not "
                                                  f"apply: {error}", timeout=6))

    def _theme(self, name: str) -> dict | None:
        try:
            return engine.load(name)
        except (KeyError, OSError, ValueError) as error:
            self.toasts.add_toast(Adw.Toast(title=f"Could not open {name}: "
                                                  f"{error}", timeout=6))
            return None

    def edit(self, name: str) -> None:
        theme = self._theme(name)
        if theme is not None:
            self.create(theme, editing=True)

    def duplicate(self, name: str) -> None:
        theme = self._theme(name)
        if theme is None:
            return
        copy = dict(theme)
        copy["label"] = f"{theme.get('label', name)} Copy"
        copy["name"] = slug(copy["label"])
        self.create(copy, editing=False)

    def confirm_delete(self, name: str) -> None:
        theme = self._theme(name)
        if theme is None:
            return
        dialog = Adw.AlertDialog(
            heading=f"Delete {theme.get('label', name)}?",
            body="The theme and the wallpaper generated for it are removed. "
                 "This cannot be undone.")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete",
                                       Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._deleted, name)
        dialog.present(self)

    def _deleted(self, _dialog, response: str, name: str) -> None:
        if response != "delete":
            return
        try:
            engine.delete(name)
        except (OSError, ValueError) as error:
            self.toasts.add_toast(Adw.Toast(title=f"Could not delete: {error}",
                                            timeout=6))
            return
        # Deleting the theme in use would leave the desktop pointing at a
        # palette that no longer exists, so fall back to the first one left.
        if engine.current() == name:
            remaining = engine.all_themes()
            if remaining:
                self.pick(remaining[0])
        self.reload()

    def _show_skins(self) -> None:
        self._show_drawn()
        self._draw_pictures()

    def edit_skin(self, name: str, kept=None) -> None:
        """Rename a Skin and choose its style, icons, cursor and font; kept
        is a Choice made before the editor was closed to add to the look."""
        # Reading every icon and cursor set, and drawing each cursor, takes
        # long enough to freeze the window.
        def gather() -> None:
            try:
                cursors = engine.cursor_sets()
                found = {"details": engine.skin_details(name),
                         "styles": engine.skin_styles(name),
                         "icon_sets": engine.icon_sets(), "cursor_sets": cursors,
                         "cursor_pictures": engine.cursor_pictures(cursors)}
            except Exception as error:                  # noqa: BLE001
                GLib.idle_add(self._not_editable, str(error))
                return
            if kept is not None:
                found["details"] = {**found["details"], "style": kept.style,
                                    "icons": kept.icons, "cursor": kept.cursor,
                                    "font": kept.font,
                                    "label": kept.label or found["details"]["label"]}
            GLib.idle_add(self._open_editor, name, found)

        threading.Thread(target=gather, daemon=True).start()

    def _not_editable(self, error: str) -> bool:
        self._toast(f"Could not open the editor: {error}")
        return False

    def _open_editor(self, name: str, found: dict) -> bool:
        details = found["details"]

        def saved(choice) -> bool:
            try:
                engine.save_skin(name, choice.label or details["label"],
                                 choice.style, choice.icons, choice.cursor,
                                 choice.font)
            except Exception as error:                  # noqa: BLE001
                self.toasts.add_toast(Adw.Toast(title=f"Not saved: {error}",
                                                timeout=6))
                return False
            if engine.chosen_skin() == name:
                self.wear(name)
            else:
                self._show_skins()
            return True

        def adding(kind: str):
            def add() -> None:
                kept = editor.choice()
                editor.close()
                self._add_to_look(kind, lambda: self.edit_skin(name, kept))
            return add

        editor = SkinEditor(
            label=details["label"], styles=found["styles"],
            style=details["style"], icon_sets=found["icon_sets"],
            icons=details["icons"], cursor_sets=found["cursor_sets"],
            cursor_pictures=found["cursor_pictures"],
            cursor=details["cursor"], font=details["font"],
            theme_icons=details["theme_icons"],
            theme_font=details["theme_font"], on_save=saved,
            on_code=lambda: self.open_in_code(name),
            on_add_icons=adding("icons"), on_add_cursors=adding("cursors"),
            on_add_fonts=adding("fonts"),
        )
        editor.present(self)
        return False

    def _add_to_look(self, kind: str, then) -> None:
        """Install downloaded icon sets, cursor sets or fonts, then reopen."""
        def chosen(paths: list[str]) -> None:
            try:
                if paths and kind == "fonts":
                    names = engine.import_fonts(paths)
                    # GTK rereads fontconfig when this changes, so the font
                    # chooser lists the new fonts without a restart.
                    Gtk.Settings.get_default().set_property(
                        "gtk-fontconfig-timestamp", int(time.time()))
                elif paths:
                    names = engine.import_icon_sets(paths[0])
                else:
                    names = []
                if names:
                    self._toast(f"Added {', '.join(names)}")
            except Exception as error:                  # noqa: BLE001
                self._toast(f"Not added: {error}")
            then()

        if kind == "fonts":
            self._choose_files("Fonts", FONTS + ARCHIVES, chosen, many=True)
        else:
            self._choose_files("Icon and cursor sets", ARCHIVES, chosen)

    def open_in_code(self, name: str) -> None:
        """For those who would rather write the style sheets (ADR 0016)."""
        try:
            Gio.Subprocess.new(["code", engine.skin_folder(name)],
                               Gio.SubprocessFlags.NONE)
        except Exception as error:                      # noqa: BLE001
            self.toasts.add_toast(Adw.Toast(title=f"Not opened: {error}",
                                            timeout=6))

    def create_skin(self) -> None:
        bases = [skin for skin in engine.skin_choices() if skin[0] != "osiris"]

        def create(label: str, base: str) -> None:
            try:
                made = engine.create_skin(label, base)
            except Exception as error:                  # noqa: BLE001
                self.toasts.add_toast(Adw.Toast(title=f"Not created: {error}",
                                                timeout=6))
                return
            self._show_skins()
            self.change_skin(made)

        new_skin(bases, create).present(self)

    def _draw_pictures(self) -> None:
        """Draw the missing pictures off the main loop, showing each as it lands."""
        if getattr(self, "_drawing", False):
            return
        stale = engine.stale_skin_pictures()
        if not stale:
            return
        self._drawing = True

        def draw() -> None:
            for name in stale:
                try:
                    picture = engine.draw_skin_picture(name)
                except Exception as error:              # noqa: BLE001
                    print(f"appearance: picture of {name}: {error}",
                          file=sys.stderr)
                    continue
                GLib.idle_add(self._landed, name, picture)
            GLib.idle_add(self._drawn)

        threading.Thread(target=draw, daemon=True).start()

    def _landed(self, name: str, picture: str) -> bool:
        page = self.skins.get_child()
        # A picture of the Theme before a switch is not this page's.
        if isinstance(page, SkinsPage) and engine.skin_pictures().get(name) == picture:
            page.show_picture(name, picture)
        return False

    def _show_drawn(self) -> bool:
        self.skins.set_child(SkinsPage(
            engine.skin_choices(), engine.chosen_skin(), self.wear,
            mine=engine.own_skins(), previews=engine.skin_pictures(),
            on_open=self.open_skin, on_export=self.export_skin,
            on_delete=self.confirm_delete_skin,
            on_duplicate=self.duplicate_skin, on_change=self.change_skin,
            on_edit=self.edit_skin, on_create=self.create_skin,
            on_import=self.import_gtk_theme))
        return False

    def _choose_files(self, title: str, suffixes: tuple[str, ...], chosen,
                      many: bool = False) -> None:
        """Ask for downloaded files; chosen gets their paths, or nothing."""
        only = Gtk.FileFilter(name=title)
        for suffix in suffixes:
            only.add_suffix(suffix.lstrip("."))
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(only)
        dialog = Gtk.FileDialog(title=title, filters=filters)

        def done(_dialog, result) -> None:
            try:
                if many:
                    files = dialog.open_multiple_finish(result)
                    paths = [files.get_item(i).get_path()
                             for i in range(files.get_n_items())]
                else:
                    paths = [dialog.open_finish(result).get_path()]
            except GLib.Error:
                paths = []
            chosen(paths)

        if many:
            dialog.open_multiple(self, None, done)
        else:
            dialog.open(self, None, done)

    def _toast(self, title: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=title, timeout=5))

    def import_gtk_theme(self) -> None:
        def chosen(paths: list[str]) -> None:
            if not paths:
                return
            try:
                name = engine.import_gtk_theme(paths[0])
            except Exception as error:                  # noqa: BLE001
                self._toast(f"Not imported: {error}")
                return
            self._show_skins()
            self._ask_osiris(name, CONVERT)

        self._choose_files("GTK themes", ARCHIVES, chosen)

    def _drawn(self) -> bool:
        self._drawing = False
        # A Theme picked while drawing leaves the new Theme's pictures to draw.
        self._draw_pictures()
        return False

    def duplicate_skin(self, name: str) -> None:
        try:
            copy = engine.duplicate_skin(name)
        except Exception as error:                      # noqa: BLE001
            self.toasts.add_toast(Adw.Toast(title=f"Not copied: {error}",
                                            timeout=6))
            return
        self._show_skins()
        labels = {skin: label for skin, label, _c in engine.skin_choices()}
        self.toasts.add_toast(Adw.Toast(
            title=f"Copied as {labels.get(copy, copy)}", timeout=3))

    def change_skin(self, name: str) -> None:
        self._ask_osiris(name)

    def _ask_osiris(self, name: str, draft: str | None = None) -> None:
        """Open Osiris on a new Conversation in the Skin's folder, with a
        request written in but not sent."""
        try:
            folder = engine.skin_folder(name)
        except Exception as error:                      # noqa: BLE001
            self._toast(f"Osiris did not open: {error}")
            return
        if draft:
            action, parameter = ("new-conversation-in-with",
                                 GLib.Variant("(ss)", (folder, draft)))
        else:
            action, parameter = "new-conversation-in", GLib.Variant("s", folder)

        # Called rather than activated through a DBusActionGroup, which never
        # says whether Osiris was there to hear it.
        def answered(connection, result) -> None:
            try:
                connection.call_finish(result)
            except GLib.Error as error:
                self._toast(f"Osiris did not open: {error.message}")

        def connected(_source, result) -> None:
            try:
                connection = Gio.bus_get_finish(result)
            except GLib.Error as error:
                self._toast(f"Osiris did not open: {error.message}")
                return
            connection.call(
                HARNESS, HARNESS_PATH, "org.gtk.Actions", "Activate",
                GLib.Variant("(sava{sv})", (action, [parameter], {})), None,
                Gio.DBusCallFlags.NONE, HARNESS_START_MS, None, answered)

        Gio.bus_get(Gio.BusType.SESSION, None, connected)

    def _skinpacks(self) -> Gio.ListStore:
        only = Gtk.FileFilter(name="Skinpacks")
        only.add_pattern("*.skinpack")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(only)
        return filters

    def open_skin(self) -> None:
        dialog = Gtk.FileDialog(title="Open a skinpack", filters=self._skinpacks())

        def chosen(_dialog, result) -> None:
            try:
                path = dialog.open_finish(result).get_path()
                name = engine.open_skin(path)
            except GLib.Error:
                return
            except Exception as error:                  # noqa: BLE001
                self.toasts.add_toast(Adw.Toast(title=f"Not opened: {error}",
                                                timeout=6))
                return
            self._show_skins()
            labels = {skin: label for skin, label, _c in engine.skin_choices()}
            self.toasts.add_toast(Adw.Toast(
                title=f"Added {labels.get(name, name)}", timeout=3))

        dialog.open(self, None, chosen)

    def export_skin(self, name: str) -> None:
        dialog = Gtk.FileDialog(title="Export Skin")

        def chosen(_dialog, result) -> None:
            try:
                folder = dialog.select_folder_finish(result).get_path()
            except GLib.Error:
                return
            shared = os.path.join(folder, f"{name}{engine.share.EXTENSION}")
            if os.path.exists(shared):
                self._confirm_replace(shared, lambda: self._export(name, folder))
            else:
                self._export(name, folder)

        dialog.select_folder(self, None, chosen)

    def _confirm_replace(self, path: str, replace) -> None:
        dialog = Adw.AlertDialog(
            heading=f"Replace {os.path.basename(path)}?",
            body="A file of that name is already in the folder.")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("replace", "Replace")
        dialog.set_response_appearance("replace",
                                       Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_close_response("cancel")
        dialog.connect("response", lambda _d, response:
                       replace() if response == "replace" else None)
        dialog.present(self)

    def _export(self, name: str, folder: str) -> None:
        try:
            shared = engine.export_skin(name, folder)
        except Exception as error:                      # noqa: BLE001
            self._toast(f"Not exported: {error}")
            return
        self._toast(f"Saved {os.path.basename(shared)}")

    def confirm_delete_skin(self, name: str) -> None:
        dialog = Adw.AlertDialog(heading="Delete this Skin?",
                                 body="It is removed from this computer.")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete",
                                       Adw.ResponseAppearance.DESTRUCTIVE)

        def answered(_dialog, response: str) -> None:
            if response != "delete":
                return
            try:
                engine.delete_skin(name)
            except Exception as error:                  # noqa: BLE001
                self.toasts.add_toast(Adw.Toast(title=f"Not deleted: {error}",
                                                timeout=6))
                return
            self.get_application().reload_user_css()
            self._show_skins()

        dialog.connect("response", answered)
        dialog.present(self)

    def wear(self, name: str) -> None:
        try:
            engine.set_skin(name)
        except Exception as error:                      # noqa: BLE001
            # The desktop may have fallen back to Osiris's own look.
            self.toasts.add_toast(Adw.Toast(title=f"Not worn: {error}",
                                            timeout=6))
        self.get_application().reload_user_css()
        self._show_skins()

    def pick(self, theme: dict) -> None:
        absent = engine.missing_packages(theme)
        if absent:
            self.toasts.add_toast(Adw.Toast(
                title=f"{theme['label']} needs: {', '.join(absent)}",
                timeout=6))
            return
        try:
            restart = engine.apply(theme["name"])
        except Exception as error:                      # noqa: BLE001
            self.toasts.add_toast(Adw.Toast(title=f"Failed: {error}",
                                            timeout=6))
            return
        # At once, rather than when the file monitor catches up.
        self.get_application().theme_scheme.follow()
        self.get_application().reload_user_css()
        self._show_skins()
        for card in self.cards:
            card.set_selected(card.theme["name"] == theme["name"])
        note = f"{theme['label']} applied"
        if restart:
            note += (f" - reopen {' and '.join(restart).lower()}"
                     " to see the new colours there")
        self.toasts.add_toast(Adw.Toast(title=note, timeout=4))


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id="dev.osiris.Appearance")
        self.user_css: UserCss | None = None

    def reload_user_css(self):
        # The file monitor would catch the rewrite too, a moment later.
        if self.user_css is not None:
            self.user_css.reload()

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.theme_scheme = ThemeScheme(Path(engine.STATE), engine.load)
        self.user_css = UserCss(
            Path(engine.HOME) / ".config" / "gtk-4.0" / "gtk.css")
        display = Gdk.Display.get_default()
        if display is not None:
            # Our widget styling above the user palette.
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS + SKINS_CSS + EDITOR_CSS)
            Gtk.StyleContext.add_provider_for_display(
                display, provider, UserCss.PRIORITY + 1)

    def do_activate(self):
        Window(self).present()


if __name__ == "__main__":
    sys.exit(Application().run(sys.argv))
