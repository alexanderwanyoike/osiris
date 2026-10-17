"""The theme creator: a palette from three colours, previewed live.

A theme carries about thirty colours. Asking for thirty is not a feature, it is
a chore, so this asks for the three that decide the character - background,
accent, and an optional secondary - plus light or dark, and derives the rest
with shell/themes/derive.py.

The derived values are written into the saved theme rather than recomputed on
load. That is what makes a theme a document: it can be hand-edited afterwards,
it does not shift under the user when the derivation is improved, and nothing
downstream has to know it was generated. See docs/THEMING.md.
"""
import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

import engine  # noqa: E402
import derive  # noqa: E402
import preview as renderer  # noqa: E402
import wallpaper  # noqa: E402

# Long enough that dragging a colour slider does not queue a render per frame,
# short enough that releasing it feels immediate. A render is about 25ms.
DEBOUNCE_MS = 120

STYLE_LABELS = {
    "contour": "Contour - topographic bands",
    "arcs": "Arcs - woven quarter circles",
    "strata": "Strata - warped horizontal layers",
    "aurora": "Aurora - soft light from the edges",
    "dots": "Dots - a sparse halftone",
    "cells": "Cells - stained glass",
    "bubbles": "Bubbles - circles that never touch",
    "ridges": "Ridges - a ridgeline landscape",
    "facets": "Facets - low-poly stone",
    "wave": "Wave - rolling ribbons of light",
}

# Starting backgrounds for each variant. Flipping the switch moves the
# background to the matching one, so the toggle does what it says rather than
# leaving a dark ground labelled "light".
DEFAULT_BACKGROUND = {True: "#15151c", False: "#f2f0ef"}

SEEDS = (
    ("background", "Background", "The darkest surface, and what the desktop "
                                 "is built out of"),
    ("accent", "Accent", "Selections, focus rings, active controls"),
    ("secondary", "Secondary", "A companion tone for the wallpaper. Optional - "
                               "left unset it is derived from the accent"),
)


def _rgba(value: str) -> Gdk.RGBA:
    colour = Gdk.RGBA()
    colour.parse(value)
    return colour


def _hex(colour: Gdk.RGBA) -> str:
    return "#" + "".join(f"{round(c * 255):02x}"
                         for c in (colour.red, colour.green, colour.blue))


class ColourRow(Adw.ActionRow):
    """A labelled row with a colour button on the end."""

    def __init__(self, title: str, subtitle: str, value: str, on_change):
        super().__init__(title=title, subtitle=subtitle)
        self.button = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(
            title=title, with_alpha=False))
        self.button.set_rgba(_rgba(value))
        self.button.set_valign(Gtk.Align.CENTER)
        self.button.connect("notify::rgba", lambda *_a: on_change())
        self.add_suffix(self.button)
        self.set_activatable_widget(self.button)

    @property
    def value(self) -> str:
        return _hex(self.button.get_rgba())


class Creator(Adw.Dialog):
    """Create a theme, or edit one that was created here before.

    `source` seeds the form. Editing a user theme reuses its name so saving
    replaces it; duplicating a shipped theme takes its colours under a new
    name, which is the documented way to fork one without touching a
    root-owned file.
    """

    def __init__(self, parent, on_saved, source: dict | None = None,
                 editing: bool = False):
        super().__init__()
        self.on_saved = on_saved
        self.editing = editing
        self.original = source["name"] if editing and source else None
        self.pending = 0
        self.preview_file = os.path.join(
            GLib.get_user_cache_dir(), "osiris", "creator-preview.png")

        self.set_title("Edit Theme" if editing else "New Theme")
        self.set_content_width(880)
        self.set_content_height(680)

        seeded = self._seed(source)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda _b: self.close())
        header.pack_start(cancel)
        self.save_button = Gtk.Button(label="Save")
        self.save_button.add_css_class("suggested-action")
        self.save_button.connect("clicked", self._save)
        header.pack_end(self.save_button)
        toolbar.add_top_bar(header)

        self.picture = Gtk.Picture()
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.picture.set_size_request(400, 250)
        self.picture.add_css_class("preview")
        frame = Gtk.Box(halign=Gtk.Align.CENTER)
        frame.set_margin_top(18)
        frame.set_margin_bottom(6)
        frame.append(self.picture)

        page = Adw.PreferencesPage()
        identity = Adw.PreferencesGroup()
        self.name_row = Adw.EntryRow(title="Name")
        self.name_row.set_text(seeded["label"])
        self.name_row.connect("changed", lambda *_a: self._validate())
        identity.add(self.name_row)

        self.variant = Adw.SwitchRow(
            title="Dark", subtitle="Light themes derive lighter neutrals and "
                                   "push the line work harder")
        self.variant.set_active(seeded["dark"])
        self.variant.connect("notify::active", self._variant_changed)
        identity.add(self.variant)
        page.add(identity)

        colours = Adw.PreferencesGroup(title="Colours")
        self.rows: dict[str, ColourRow] = {}
        for key, title, subtitle in SEEDS:
            row = ColourRow(title, subtitle, seeded[key], self._schedule)
            self.rows[key] = row
            colours.add(row)

        self.use_secondary = Adw.SwitchRow(
            title="Use a secondary colour",
            subtitle="Off derives one from the accent")
        self.use_secondary.set_active(seeded["has_secondary"])
        self.use_secondary.connect("notify::active", self._toggle_secondary)
        colours.add(self.use_secondary)
        page.add(colours)

        background = Adw.PreferencesGroup(title="Wallpaper")
        self.style = Adw.ComboRow(title="Pattern")
        model = Gtk.StringList()
        # The built-in styles, then any wallpaper packages, made by hand or by
        # an agent, under their own labels.
        self.styles = wallpaper.styles()
        found, _ = wallpaper.packages.discover(wallpaper.PACKAGE_DIRS)
        for style in self.styles:
            model.append(STYLE_LABELS.get(style)
                         or (found[style].label if style in found else style))
        self.style.set_model(model)
        if seeded["style"] in self.styles:
            self.style.set_selected(self.styles.index(seeded["style"]))
        self.style.connect("notify::selected", lambda *_a: self._schedule())
        background.add(self.style)
        page.add(background)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(frame)
        content.append(page)
        scroller = Gtk.ScrolledWindow(vexpand=True)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(content)

        self.toasts = Adw.ToastOverlay()
        self.toasts.set_child(scroller)
        toolbar.set_content(self.toasts)
        self.set_child(toolbar)

        self.rows["secondary"].set_sensitive(seeded["has_secondary"])
        self._render()
        self._validate()

    # ----------------------------------------------------------------- state

    def _seed(self, source: dict | None) -> dict:
        """Starting values for the form.

        A theme edited here records what it was derived from, so reopening it
        restores the seeds rather than the thirty colours they produced. A
        shipped theme has no such record, so fall back to reading the seeds
        back off its palette - background and accent are stored verbatim.
        """
        if source is None:
            return {"label": "My Theme", "dark": True, "background": "#15151c",
                    "accent": "#7aa2f7", "secondary": "#bb9af7",
                    "has_secondary": False, "style": "contour"}
        colors = source.get("colors", {})
        seeds = source.get("derived_from", {})
        secondary = seeds.get("secondary") or colors.get("accentSecondary")
        return {
            "label": source.get("label", source["name"]),
            "dark": source.get("dark", True),
            "background": seeds.get("background") or colors.get(
                "background", "#15151c"),
            "accent": seeds.get("accent") or colors.get("accent", "#7aa2f7"),
            "secondary": secondary or colors.get("accent", "#bb9af7"),
            "has_secondary": secondary is not None,
            "style": source.get("wallpaper_style") or wallpaper.style_for(
                source["name"]),
        }

    def _variant_changed(self, *_args) -> None:
        """Move the background to the new variant if it is on the wrong side.

        A background the user has already chosen to suit the variant is left
        alone; one that contradicts it is replaced. derive.py no longer
        produces unreadable text when the two disagree, but a light theme on a
        near-black ground is still not what anyone meant by "light".
        """
        dark = self.variant.get_active()
        background = self.rows["background"].value
        if (derive.luminance(background) < derive.MID_LUMINANCE) != dark:
            self.rows["background"].button.set_rgba(
                _rgba(DEFAULT_BACKGROUND[dark]))      # fires its own _schedule
        else:
            self._schedule()

    def _toggle_secondary(self, *_args) -> None:
        self.rows["secondary"].set_sensitive(self.use_secondary.get_active())
        self._schedule()

    def build(self) -> dict:
        """The theme the form currently describes."""
        label = self.name_row.get_text().strip() or "Untitled"
        theme = derive.build(
            engine.slug(label), label,
            self.rows["background"].value, self.rows["accent"].value,
            dark=self.variant.get_active(),
            secondary=(self.rows["secondary"].value
                       if self.use_secondary.get_active() else None))
        theme["wallpaper_style"] = self.styles[self.style.get_selected()]
        return theme

    # ---------------------------------------------------------------- render

    def _schedule(self, *_args) -> None:
        if self.pending:
            GLib.source_remove(self.pending)
        self.pending = GLib.timeout_add(DEBOUNCE_MS, self._render)
        self._validate()

    def _render(self) -> bool:
        self.pending = 0
        try:
            renderer.render_theme(self.build(), self.preview_file)
        except Exception as error:                          # noqa: BLE001
            print(f"osiris-appearance: preview: {error}", file=sys.stderr)
            return GLib.SOURCE_REMOVE
        # set_filename alone will not reload a path it is already showing.
        self.picture.set_filename(None)
        self.picture.set_filename(self.preview_file)
        return GLib.SOURCE_REMOVE

    def _validate(self) -> None:
        """Enable Save only when the name is usable and not already taken."""
        label = self.name_row.get_text().strip()
        name = engine.slug(label)
        taken = engine.exists(name) and name != self.original
        problem = ("" if label and not taken else
                   "Enter a name" if not label else
                   "A theme called that already exists")
        self.save_button.set_sensitive(not problem)
        if problem and label:
            self.name_row.add_css_class("error")
        else:
            self.name_row.remove_css_class("error")

    # ------------------------------------------------------------------ save

    def _save(self, _button) -> None:
        theme = self.build()
        # A rename leaves the old file behind, and it would keep showing in the
        # picker alongside its replacement.
        if self.original and self.original != theme["name"]:
            try:
                engine.delete(self.original)
            except (OSError, ValueError) as error:
                print(f"osiris-appearance: replacing {self.original}: {error}",
                      file=sys.stderr)
        try:
            engine.save(theme)
        except (OSError, ValueError) as error:
            self.toasts.add_toast(Adw.Toast(title=f"Could not save: {error}",
                                            timeout=6))
            return
        self.close()
        self.on_saved(theme["name"])
