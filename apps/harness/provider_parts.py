"""The parts of a Provider's card that every kind of Provider shares."""
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402


def connected_chip() -> Gtk.Widget:
    chip = Gtk.Box(spacing=4, valign=Gtk.Align.CENTER)
    chip.add_css_class("harness-connected")
    chip.append(Gtk.Image(icon_name="object-select-symbolic"))
    chip.append(Gtk.Label(label="Connected"))
    return chip


def add_key(section: Gtk.Box, on_save: Callable[[str], None]) -> None:
    """An Add key button, which opens a field for the key."""
    entry = Gtk.PasswordEntry(placeholder_text="API key", hexpand=True,
                              show_peek_icon=True)
    save = Gtk.Button(label="Save")
    save.connect("clicked", lambda _b: on_save(entry.get_text().strip()))
    form = Gtk.Box(spacing=6, visible=False)
    form.add_css_class("harness-key-form")
    form.append(entry)
    form.append(save)
    add = Gtk.Button(label="Add key", halign=Gtk.Align.START)
    add.add_css_class("flat")
    add.connect("clicked", lambda _b: (form.set_visible(True), add.set_visible(False)))
    section.append(add)
    section.append(form)
