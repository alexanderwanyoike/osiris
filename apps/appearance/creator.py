"""The theme creator: a theme from one colour, a picture, or chosen colours.

A theme carries about thirty colours. Asking for thirty is not a feature, it is
a chore. So there are three ways to start, and each asks for little:

* **One colour** - a seed, a harmony and a mood; osiris/themes/intent.py makes
  the colours, harmonious and legible by construction.
* **A picture** - which proposes the seed, light or dark, and the mood
  (osiris/themes/from_wallpaper.py), all of which can be changed, and becomes
  the theme's wallpaper.
* **Colours I choose** - background, accent and an optional secondary, with
  colours that go with the accent offered alongside. Nothing stops a clash.

In every mode the rest of the palette is derived the same way.

The derived values are written into the saved theme rather than recomputed on
load. That is what makes a theme a document: it can be hand-edited afterwards,
it does not shift under the user when the derivation is improved, and nothing
downstream has to know it was generated. See docs/THEMING.md.
"""
import os
import shutil
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

import engine  # noqa: E402
import derive  # noqa: E402
import preview as renderer  # noqa: E402
import wallpaper  # noqa: E402
from PIL import Image  # noqa: E402

# engine has put the osiris package on sys.path.
from osiris.model.colour import Colour  # noqa: E402
from osiris.themes import derive as rules  # noqa: E402
from osiris.themes.from_wallpaper import intent_from  # noqa: E402
from osiris.themes.intent import (  # noqa: E402
    Harmony, Mood, ThemeIntent, partners, seeds)

MODES = ("colour", "picture", "custom")
MODE_LABELS = ("One colour", "A picture", "Colours I choose")
HARMONY_LABELS = {
    Harmony.ANALOGOUS: "Analogous - neighbours on the colour wheel",
    Harmony.COMPLEMENTARY: "Complementary - opposites",
    Harmony.SPLIT_COMPLEMENTARY: "Split complementary - either side of opposite",
    Harmony.TRIADIC: "Triadic - three evenly spaced",
    Harmony.MONOCHROME: "Monochrome - one hue, lighter and darker",
}
MOOD_LABELS = {
    Mood.MUTED: "Muted", Mood.BALANCED: "Balanced",
    Mood.VIVID: "Vivid", Mood.PASTEL: "Pastel",
}

# Long enough that dragging a colour slider does not queue a render per frame,
# short enough that releasing it feels immediate. A render is about 25ms.
DEBOUNCE_MS = 120

STYLE_LABELS = {
    "contour": "Contour - topographic bands",
    "arcs": "Arcs - woven quarter circles",
    "strata": "Strata - warped horizontal layers",
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

    def set_value(self, value: str) -> None:
        self.button.set_rgba(_rgba(value))


class Swatch(Gtk.Button):
    """A small button showing one colour."""

    def __init__(self, colour: str, tooltip: str, on_pick):
        super().__init__(tooltip_text=tooltip, valign=Gtk.Align.CENTER)
        self.add_css_class("flat")
        area = Gtk.DrawingArea(content_width=28, content_height=20)
        red, green, blue = Colour(colour).rgb

        def draw(_area, cr, width, height):
            cr.set_source_rgb(red, green, blue)
            cr.rectangle(0, 0, width, height)
            cr.fill()

        area.set_draw_func(draw)
        self.set_child(area)
        self.connect("clicked", lambda _b: on_pick(colour))


class PartnersRow(Adw.ActionRow):
    """Colours that go with the accent, any of which becomes the secondary."""

    def __init__(self, on_pick):
        super().__init__(title="Goes with your accent",
                         subtitle="Pick one to use it as the secondary")
        self.on_pick = on_pick
        self.box = Gtk.Box(spacing=2, valign=Gtk.Align.CENTER)
        self.add_suffix(self.box)

    def show_for(self, accent: str) -> None:
        while (child := self.box.get_first_child()) is not None:
            self.box.remove(child)
        for harmony, colours in partners(Colour(accent)).items():
            name = harmony.value.replace("-", " ")
            for colour in colours:
                self.box.append(Swatch(colour.hex, name, self.on_pick))


def _combo(title: str, labels) -> Adw.ComboRow:
    row = Adw.ComboRow(title=title)
    model = Gtk.StringList()
    for label in labels:
        model.append(label)
    row.set_model(model)
    return row


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
        self.set_content_height(720)

        seeded = self._seed(source)
        self.picture_path: str | None = seeded["picture"]
        self.picture_seed: str | None = seeded["picture_seed"]

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

        self.mode = _combo("Start from", MODE_LABELS)
        self.mode.set_selected(MODES.index(seeded["mode"]))
        self.mode.connect("notify::selected", self._mode_changed)
        identity.add(self.mode)

        self.variant = Adw.SwitchRow(
            title="Dark", subtitle="Light themes derive lighter neutrals and "
                                   "push the line work harder")
        self.variant.set_active(seeded["dark"])
        self.variant.connect("notify::active", self._variant_changed)
        identity.add(self.variant)
        page.add(identity)

        # One colour, and a picture: what the theme should be.
        self.intent_group = Adw.PreferencesGroup(title="Character")
        self.seed_row = ColourRow("Colour", "The theme is built around this hue",
                                  seeded["seed"], self._schedule)
        self.intent_group.add(self.seed_row)
        self.picture_row = Adw.ActionRow(title="Picture")
        choose = Gtk.Button(label="Choose…", valign=Gtk.Align.CENTER)
        choose.connect("clicked", self._choose_picture)
        self.picture_row.add_suffix(choose)
        self.intent_group.add(self.picture_row)
        self.harmony = _combo("Harmony", HARMONY_LABELS.values())
        self.harmony.set_selected(list(Harmony).index(seeded["harmony"]))
        self.harmony.connect("notify::selected", lambda *_a: self._schedule())
        self.intent_group.add(self.harmony)
        self.mood = _combo("Mood", MOOD_LABELS.values())
        self.mood.set_selected(list(Mood).index(seeded["mood"]))
        self.mood.connect("notify::selected", lambda *_a: self._schedule())
        self.intent_group.add(self.mood)
        page.add(self.intent_group)

        # Colours I choose.
        self.custom_group = Adw.PreferencesGroup(title="Colours")
        self.rows: dict[str, ColourRow] = {}
        for key, title, subtitle in SEEDS:
            row = ColourRow(title, subtitle, seeded[key], self._custom_changed)
            self.rows[key] = row
            self.custom_group.add(row)
        self.partners = PartnersRow(self._use_partner)
        self.custom_group.add(self.partners)
        self.use_secondary = Adw.SwitchRow(
            title="Use a secondary colour",
            subtitle="Off derives one from the accent")
        self.use_secondary.set_active(seeded["has_secondary"])
        self.use_secondary.connect("notify::active", self._toggle_secondary)
        self.custom_group.add(self.use_secondary)
        page.add(self.custom_group)

        self.background_group = Adw.PreferencesGroup(title="Wallpaper")
        self.style = Adw.ComboRow(title="Pattern")
        model = Gtk.StringList()
        for style in wallpaper.STYLES:
            model.append(STYLE_LABELS[style])
        self.style.set_model(model)
        self.style.set_selected(wallpaper.STYLES.index(seeded["style"]))
        self.style.connect("notify::selected", lambda *_a: self._schedule())
        self.background_group.add(self.style)
        page.add(self.background_group)

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
        self.partners.show_for(seeded["accent"])
        self._show_mode()
        self._render()
        self._validate()

    # ----------------------------------------------------------------- state

    def _seed(self, source: dict | None) -> dict:
        """Starting values for the form.

        A theme made here records its intent, or the colours it was derived
        from, so reopening it restores the form rather than thirty colours. A
        shipped theme has neither, so its background and accent - stored
        verbatim - are read back off its palette.
        """
        values = {"label": "My Theme", "dark": True, "background": "#15151c",
                  "accent": "#7aa2f7", "secondary": "#bb9af7",
                  "has_secondary": False, "style": "contour", "mode": "colour",
                  "seed": "#7aa2f7", "harmony": Harmony.ANALOGOUS,
                  "mood": Mood.BALANCED, "picture": None, "picture_seed": None}
        if source is None:
            return values
        colors = source.get("colors", {})
        derived = source.get("derived_from", {})
        secondary = derived.get("secondary") or colors.get("accentSecondary")
        values.update({
            "label": source.get("label", source["name"]),
            "dark": source.get("dark", True),
            "background": derived.get("background") or colors.get(
                "background", "#15151c"),
            "accent": derived.get("accent") or colors.get("accent", "#7aa2f7"),
            "secondary": secondary or colors.get("accent", "#bb9af7"),
            "has_secondary": secondary is not None,
            "style": source.get("wallpaper_style") or wallpaper.style_for(
                source["name"]),
            "mode": "custom",
        })
        intent = source.get("intent")
        if intent:
            picture = engine.picture_of(source)
            values.update({
                "mode": "picture" if picture else "colour",
                "seed": intent["seed"],
                "harmony": Harmony(intent["harmony"]),
                "mood": Mood(intent["mood"]),
                "picture": picture,
                "picture_seed": intent["seed"] if picture else None,
            })
        return values

    @property
    def current_mode(self) -> str:
        return MODES[self.mode.get_selected()]

    def _show_mode(self) -> None:
        mode = self.current_mode
        self.intent_group.set_visible(mode != "custom")
        self.seed_row.set_visible(mode == "colour")
        self.picture_row.set_visible(mode == "picture")
        self.picture_row.set_subtitle(
            os.path.basename(self.picture_path) if self.picture_path
            else "None chosen yet")
        self.custom_group.set_visible(mode == "custom")
        # A theme made from a picture wears the picture, not a pattern.
        self.background_group.set_visible(mode != "picture")

    def _mode_changed(self, *_args) -> None:
        self._show_mode()
        self._schedule()

    def _variant_changed(self, *_args) -> None:
        """Move a chosen background to the new variant if it is on the wrong
        side. One colour and a picture need nothing: their background comes
        from the variant."""
        dark = self.variant.get_active()
        background = self.rows["background"].value
        if (self.current_mode == "custom"
                and (derive.luminance(background) < derive.MID_LUMINANCE) != dark):
            self.rows["background"].set_value(DEFAULT_BACKGROUND[dark])
        else:
            self._schedule()

    def _custom_changed(self) -> None:
        self.partners.show_for(self.rows["accent"].value)
        self._schedule()

    def _use_partner(self, colour: str) -> None:
        self.use_secondary.set_active(True)
        self.rows["secondary"].set_value(colour)

    def _toggle_secondary(self, *_args) -> None:
        self.rows["secondary"].set_sensitive(self.use_secondary.get_active())
        self._schedule()

    def _choose_picture(self, _button) -> None:
        images = Gtk.FileFilter(name="Pictures")
        images.add_mime_type("image/*")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(images)
        dialog = Gtk.FileDialog(title="Choose a picture", filters=filters)
        dialog.open(self.get_root(), None, self._picture_chosen)

    def _picture_chosen(self, dialog, result) -> None:
        try:
            chosen = dialog.open_finish(result)
        except GLib.Error:
            return                                  # dismissed
        path = chosen.get_path()
        try:
            proposed = intent_from(Image.open(path))
        except (OSError, ValueError) as error:
            self.toasts.add_toast(Adw.Toast(
                title=f"Could not read that picture: {error}", timeout=6))
            return
        self.picture_path = path
        self.picture_seed = proposed.seed.hex
        # The picture proposes; everything stays adjustable afterwards.
        self.variant.set_active(proposed.dark)
        self.mood.set_selected(list(Mood).index(proposed.mood))
        self._show_mode()
        self._schedule()

    def _intent(self) -> ThemeIntent | None:
        mode = self.current_mode
        seed = (self.seed_row.value if mode == "colour"
                else self.picture_seed if mode == "picture" else None)
        if seed is None:
            return None
        return ThemeIntent(
            seed=Colour(seed),
            harmony=list(Harmony)[self.harmony.get_selected()],
            mood=list(Mood)[self.mood.get_selected()],
            dark=self.variant.get_active(),
        )

    def build(self) -> dict:
        """The theme the form currently describes."""
        label = self.name_row.get_text().strip() or "Untitled"
        style = wallpaper.STYLES[self.style.get_selected()]
        intent = self._intent()
        if intent is None:
            theme = derive.build(
                engine.slug(label), label,
                self.rows["background"].value, self.rows["accent"].value,
                dark=self.variant.get_active(),
                secondary=(self.rows["secondary"].value
                           if self.use_secondary.get_active() else None))
            theme["wallpaper_style"] = style
            return theme
        theme = rules.build(engine.slug(label), label, seeds(intent),
                            wallpaper_style=style)
        theme["intent"] = {"seed": intent.seed.hex,
                           "harmony": intent.harmony.value,
                           "mood": intent.mood.value}
        if self.current_mode == "picture" and self.picture_path:
            theme["wallpaper"] = self.picture_path
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
        """Enable Save only when the name is usable and not already taken, and
        a picture theme has its picture."""
        label = self.name_row.get_text().strip()
        name = engine.slug(label)
        taken = engine.exists(name) and name != self.original
        problem = ("" if label and not taken else
                   "Enter a name" if not label else
                   "A theme called that already exists")
        no_picture = self.current_mode == "picture" and not self.picture_path
        self.save_button.set_sensitive(not problem and not no_picture)
        if problem and label:
            self.name_row.add_css_class("error")
        else:
            self.name_row.remove_css_class("error")

    # ------------------------------------------------------------------ save

    def _keep_picture(self, theme: dict) -> None:
        """Copy the picture beside the user's other theme assets, so moving or
        deleting the original does not take the theme's wallpaper with it."""
        picture = theme.get("wallpaper")
        if not picture or not os.path.isabs(picture):
            return
        extension = os.path.splitext(picture)[1].lower() or ".png"
        kept = os.path.join(engine.USER_WALLPAPERS,
                            f"{theme['name']}-picture{extension}")
        # Copied even from another theme's kept picture: a rename deletes the
        # old theme, and its picture with it.
        if picture != kept:
            os.makedirs(engine.USER_WALLPAPERS, exist_ok=True)
            shutil.copy(picture, kept)
        theme["wallpaper"] = kept

    def _save(self, _button) -> None:
        theme = self.build()
        try:
            self._keep_picture(theme)
        except OSError as error:
            self.toasts.add_toast(Adw.Toast(
                title=f"Could not keep the picture: {error}", timeout=6))
            return
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
