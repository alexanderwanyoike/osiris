"""Draw a window of widgets with one GTK 3 theme, off-screen, to a picture.

    python3 sampler.py THEME[:dark] OUT.png

Appearance runs it for each Skin, with the Skin built in the current Theme's
colours, so a Skin's picture always matches the Theme. GTK 3 and GTK 4 cannot
share a process, hence a program of its own.
"""

import os
import sys

# GTK reads the theme once, when it starts.
os.environ["GTK_THEME"] = sys.argv[1]

import gi  # noqa: E402

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

WIDTH, HEIGHT = 560, 360


def header() -> Gtk.HeaderBar:
    bar = Gtk.HeaderBar(title="Documents", subtitle="Home",
                        show_close_button=True)
    bar.set_decoration_layout("menu:minimize,maximize,close")
    bar.get_style_context().add_class("titlebar")
    back = Gtk.Button.new_from_icon_name("go-previous-symbolic",
                                         Gtk.IconSize.BUTTON)
    bar.pack_start(back)
    search = Gtk.ToggleButton(active=True)
    search.add(Gtk.Image.new_from_icon_name("edit-find-symbolic",
                                            Gtk.IconSize.BUTTON))
    bar.pack_end(search)
    return bar


def sidebar() -> Gtk.ListBox:
    places = Gtk.ListBox(width_request=150)
    places.get_style_context().add_class("navigation-sidebar")
    for icon, name in (("user-home-symbolic", "Home"),
                       ("folder-documents-symbolic", "Documents"),
                       ("folder-music-symbolic", "Music"),
                       ("folder-pictures-symbolic", "Pictures")):
        row = Gtk.Box(spacing=8, margin=8)
        row.add(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU))
        row.add(Gtk.Label(label=name, xalign=0))
        places.add(row)
    places.select_row(places.get_row_at_index(0))
    return places


def controls() -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=16)
    stack = Gtk.Stack()
    for name in ("Files", "Recent", "Starred"):
        stack.add_titled(Gtk.Box(), name, name)
    tabs = Gtk.StackSwitcher(stack=stack, halign=Gtk.Align.START)
    box.add(tabs)
    entry = Gtk.Entry(text="Holiday photos")
    box.add(entry)
    buttons = Gtk.Box(spacing=8)
    buttons.add(Gtk.Button(label="Cancel"))
    open_ = Gtk.Button(label="Open")
    open_.get_style_context().add_class("suggested-action")
    buttons.add(open_)
    remove = Gtk.Button(label="Delete")
    remove.get_style_context().add_class("destructive-action")
    buttons.add(remove)
    box.add(buttons)
    toggles = Gtk.Box(spacing=16)
    toggles.add(Gtk.Switch(active=True, valign=Gtk.Align.CENTER))
    toggles.add(Gtk.CheckButton(label="Hidden files", active=True))
    first = Gtk.RadioButton(label="List")
    toggles.add(first)
    toggles.add(Gtk.RadioButton.new_with_label_from_widget(first, "Grid"))
    box.add(toggles)
    box.add(Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1))
    box.get_children()[-1].set_value(60)
    box.get_children()[-1].set_draw_value(False)
    progress = Gtk.ProgressBar(fraction=0.7)
    box.add(progress)
    return box


def main() -> None:
    window = Gtk.OffscreenWindow()
    window.set_default_size(WIDTH, HEIGHT)
    frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                    width_request=WIDTH, height_request=HEIGHT)
    frame.get_style_context().add_class("background")
    frame.add(header())
    body = Gtk.Box(vexpand=True)
    body.add(sidebar())
    body.add(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
    body.pack_start(controls(), True, True, 0)
    frame.add(body)
    window.add(frame)
    window.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()
    picture = window.get_pixbuf().new_subpixbuf(0, 0, WIDTH, HEIGHT)
    picture.savev(sys.argv[2], "png", [], [])


if __name__ == "__main__":
    main()
