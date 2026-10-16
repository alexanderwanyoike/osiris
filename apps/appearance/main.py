#!/usr/bin/env python3
"""Osiris Appearance - pick a theme from live previews.

GTK4 + libadwaita. Each theme is a card showing a rendered miniature of the
desktop in that palette; clicking one applies it immediately.

Run directly, or install the .desktop file alongside it.
"""
import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

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

CSS = b"""
.theme-card {
    padding: 0;
    border-radius: 12px;
    background: transparent;
    border: 2px solid transparent;
}
.theme-card:hover { background: alpha(currentColor, 0.06); }
.theme-card.selected { border-color: @accent_color; }
.preview { border-radius: 8px; }
.theme-name { font-weight: 700; }
.variant-badge {
    font-size: 0.78em;
    padding: 1px 8px;
    border-radius: 999px;
    background: alpha(currentColor, 0.12);
}
.card-menu {
    opacity: 0;
    min-width: 26px;
    min-height: 26px;
    padding: 0;
    transition: opacity 120ms ease;
}
overlay:hover .card-menu,
.card-menu:focus-within,
.card-menu:checked { opacity: 1; }
"""


class ThemeCard(Gtk.Overlay):
    """A clickable theme card with a menu button in its corner.

    An Overlay wrapping a Button, rather than a Button containing both. A
    GtkButton takes the pointer across its whole area, so a menu button nested
    inside one is visible, highlights on hover, and never fires. Overlay
    children sit above the main child and are offered input first, which gives
    the card one large hit target and the menu its own small one.
    """

    def __init__(self, theme: dict, on_pick):
        super().__init__()
        self.theme = theme

        self.button = Gtk.Button()
        self.button.add_css_class("theme-card")
        self.button.add_css_class("flat")
        self.button.connect("clicked", lambda _b: on_pick(theme))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        preview = theme.get("preview")
        if preview and os.path.exists(preview):
            picture = Gtk.Picture.new_for_filename(preview)
            picture.set_content_fit(Gtk.ContentFit.COVER)
            picture.set_size_request(280, 175)
            picture.add_css_class("preview")
            box.append(picture)
        else:
            placeholder = Gtk.Box()
            placeholder.set_size_request(280, 175)
            box.append(placeholder)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name = Gtk.Label(label=theme["label"], xalign=0)
        name.add_css_class("theme-name")
        row.append(name)
        row.append(Gtk.Box(hexpand=True))
        badge = Gtk.Label(label="Dark" if theme.get("dark", True) else "Light")
        badge.add_css_class("variant-badge")
        row.append(badge)
        # Room for the overlaid menu button, which would otherwise cover this.
        row.set_margin_end(32)
        box.append(row)

        self.button.set_child(box)
        self.set_child(self.button)
        self.add_overlay(self._menu(theme))

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
        # Now, rather than at the next tick: the drift process itself only
        # looks every few minutes.
        GLib.spawn_async([sys.executable, drift.__file__, "--once"],
                         flags=GLib.SpawnFlags.DEFAULT)

    def __init__(self, app):
        super().__init__(application=app, title="Appearance")
        self.set_default_size(1000, 720)
        self.cards: list[ThemeCard] = []

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="Appearance",
                                                subtitle="Osiris themes"))
        new_button = Gtk.Button(icon_name="list-add-symbolic",
                                tooltip_text="New theme")
        new_button.connect("clicked", lambda _b: self.create())
        header.pack_start(new_button)
        self.drift = Gtk.ToggleButton(
            label="Drift", active=drift.enabled(),
            tooltip_text="Let generated wallpapers drift slowly")
        self.drift.connect("toggled", self._drift_toggled)
        header.pack_end(self.drift)
        toolbar.add_top_bar(header)

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

        self.flow = Gtk.FlowBox()
        self.flow.set_valign(Gtk.Align.START)
        self.flow.set_max_children_per_line(3)
        self.flow.set_min_children_per_line(2)
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_row_spacing(10)
        self.flow.set_column_spacing(10)
        self.flow.set_margin_top(18)
        self.flow.set_margin_bottom(18)
        self.flow.set_margin_start(18)
        self.flow.set_margin_end(18)
        self.flow.set_homogeneous(True)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(self.flow)
        scroller.set_vexpand(True)

        self.toasts.set_child(scroller)
        toolbar.set_content(self.toasts)
        self.set_content(toolbar)
        self.reload()

    def reload(self) -> None:
        """Rebuild the grid from what is on disk."""
        while (child := self.flow.get_first_child()) is not None:
            self.flow.remove(child)
        self.cards = []

        active = engine.current()
        themes = engine.all_themes()
        if not themes:
            self.flow.append(Gtk.Label(label="No themes found."))
            return
        for theme in themes:
            card = ThemeCard(theme, self.pick)
            card.set_selected(theme["name"] == active)
            self.cards.append(card)
            self.flow.append(card)

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
        copy["name"] = engine.slug(copy["label"])
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
        # GTK reads ~/.config/gtk-4.0/gtk.css once at startup. The app rewrites
        # that file when a theme is applied, so without an explicit provider it
        # would keep its old palette - including its own header bar - until
        # restarted. Holding our own provider lets us reload it in place.
        self.user_css = Gtk.CssProvider()

    def reload_user_css(self):
        path = os.path.join(engine.HOME, ".config", "gtk-4.0", "gtk.css")
        if not os.path.exists(path):
            return
        try:
            self.user_css.load_from_path(path)
        except GLib.Error:
            pass

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
        if display is not None:
            # User palette first, then our widget styling on top.
            Gtk.StyleContext.add_provider_for_display(
                display, self.user_css,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS)
            Gtk.StyleContext.add_provider_for_display(
                display, provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)
        self.reload_user_css()
        Window(self).present()


if __name__ == "__main__":
    sys.exit(Application().run(sys.argv))
