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
from skins_page import CSS as SKINS_CSS, SkinsPage  # noqa: E402

# creator has put the osiris package on sys.path.
from osiris.apps.user_css import UserCss  # noqa: E402
from osiris.model.names import slug  # noqa: E402
from osiris.themes.library import Filter, arrange  # noqa: E402

HARNESS = "dev.osiris.Harness"
HARNESS_PATH = "/dev/osiris/Harness"

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
        self.skins.set_child(SkinsPage(
            engine.skin_choices(), engine.chosen_skin(), self.wear,
            mine=engine.own_skins(), previews=engine.skin_previews(),
            on_open=self.open_skin,
            on_export=self.export_skin, on_delete=self.confirm_delete_skin,
            on_duplicate=self.duplicate_skin, on_change=self.change_skin,
            on_edit=self.edit_skin, on_create=self.create_skin))

    def edit_skin(self, name: str) -> None:
        """Open the Skin's folder in the code editor Osiris ships (ADR 0016)."""
        try:
            Gio.Subprocess.new(["code", engine.skin_folder(name)],
                               Gio.SubprocessFlags.NONE)
        except Exception as error:                      # noqa: BLE001
            self.toasts.add_toast(Adw.Toast(title=f"Not opened: {error}",
                                            timeout=6))

    def create_skin(self) -> None:
        bases = [skin for skin in engine.skin_choices() if skin[0] != "osiris"]
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

        def answered(_dialog, response: str) -> None:
            label = name.get_text().strip()
            if response != "create" or not label:
                return
            try:
                made = engine.create_skin(label, bases[base.get_selected()][0])
            except Exception as error:                  # noqa: BLE001
                self.toasts.add_toast(Adw.Toast(title=f"Not created: {error}",
                                                timeout=6))
                return
            self._show_skins()
            self.change_skin(made)

        dialog.connect("response", answered)
        dialog.present(self)

    def duplicate_skin(self, name: str) -> None:
        try:
            copy = engine.duplicate_skin(name)
        except Exception as error:                      # noqa: BLE001
            self.toasts.add_toast(Adw.Toast(title=f"Not copied: {error}",
                                            timeout=6))
            return
        self._show_skins()
        self.toasts.add_toast(Adw.Toast(title=f"Copied as {copy}", timeout=3))

    def change_skin(self, name: str) -> None:
        """Open Osiris on a new Conversation in the Skin's folder."""
        try:
            connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            actions = Gio.DBusActionGroup.get(connection, HARNESS, HARNESS_PATH)
            actions.activate_action("new-conversation-in",
                                    GLib.Variant("s", engine.skin_folder(name)))
        except Exception as error:                      # noqa: BLE001
            self.toasts.add_toast(Adw.Toast(title=f"Osiris did not open: {error}",
                                            timeout=6))

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
            self.toasts.add_toast(Adw.Toast(title=f"Added {name}", timeout=3))

        dialog.open(self, None, chosen)

    def export_skin(self, name: str) -> None:
        dialog = Gtk.FileDialog(title="Export Skin")

        def chosen(_dialog, result) -> None:
            try:
                folder = dialog.select_folder_finish(result).get_path()
                shared = engine.export_skin(name, folder)
            except GLib.Error:
                return
            except Exception as error:                  # noqa: BLE001
                self.toasts.add_toast(Adw.Toast(title=f"Not exported: {error}",
                                                timeout=6))
                return
            self.toasts.add_toast(Adw.Toast(
                title=f"Saved {os.path.basename(shared)}", timeout=4))

        dialog.select_folder(self, None, chosen)

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
            self.toasts.add_toast(Adw.Toast(title=f"Failed: {error}",
                                            timeout=6))
            return
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
        Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.FORCE_DARK if theme.get("dark", True)
            else Adw.ColorScheme.FORCE_LIGHT)
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

    def do_activate(self):
        # libadwaita normally takes light/dark from the XDG settings portal.
        # Cinnamon does not serve that, so the app would always render light on
        # a dark desktop. Follow the active Osiris theme instead.
        active = engine.current()
        dark = True
        if active:
            try:
                dark = engine.load(active).get("dark", True)
            except KeyError:
                pass
        Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.FORCE_DARK if dark else Adw.ColorScheme.FORCE_LIGHT)

        display = Gdk.Display.get_default()
        self.user_css = UserCss(
            Path(engine.HOME) / ".config" / "gtk-4.0" / "gtk.css")
        if display is not None:
            # Our widget styling above the user palette.
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS + SKINS_CSS)
            Gtk.StyleContext.add_provider_for_display(
                display, provider, UserCss.PRIORITY + 1)
        Window(self).present()


if __name__ == "__main__":
    sys.exit(Application().run(sys.argv))
