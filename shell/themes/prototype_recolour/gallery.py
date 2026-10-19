"""PROTOTYPE, throwaway: a GTK 3 sample window, rendered to a PNG offscreen.

    GTK_THEME=<theme> xvfb-run python3 gallery.py <shape.css> <palette.css> <out.png> <title>
"""
import sys, gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
shape, palette, out = sys.argv[1], sys.argv[2], sys.argv[3]
provider = Gtk.CssProvider(); provider.load_from_data((open(palette).read() + open(shape).read()).encode())
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, 800)
win = Gtk.OffscreenWindow()
outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
bar = Gtk.HeaderBar(title=sys.argv[4], show_close_button=True)
bar.pack_start(Gtk.Button.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.BUTTON))
outer.pack_start(bar, False, False, 0)
book = Gtk.Notebook()
page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=18)
row = Gtk.Box(spacing=10)
ok = Gtk.Button(label="Save"); ok.get_style_context().add_class("suggested-action")
row.pack_start(ok, False, False, 0); row.pack_start(Gtk.Button(label="Cancel"), False, False, 0)
sw = Gtk.Switch(active=True); row.pack_end(sw, False, False, 0)
page.pack_start(row, False, False, 0)
page.pack_start(Gtk.Entry(text="Search files"), False, False, 0)
checks = Gtk.Box(spacing=16)
checks.pack_start(Gtk.CheckButton(label="Show hidden", active=True), False, False, 0)
checks.pack_start(Gtk.RadioButton(label="List"), False, False, 0)
page.pack_start(checks, False, False, 0)
scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1); scale.set_value(60); scale.set_draw_value(False)
page.pack_start(scale, False, False, 0)
bar2 = Gtk.ProgressBar(); bar2.set_fraction(0.4); page.pack_start(bar2, False, False, 0)
frame = Gtk.Frame(); lb = Gtk.ListBox()
for name in ("Documents", "Pictures", "Projects"):
    lb.add(Gtk.Label(label=name, xalign=0, margin=8))
frame.add(lb); page.pack_start(frame, False, False, 0)
book.append_page(page, Gtk.Label(label="General")); book.append_page(Gtk.Box(), Gtk.Label(label="Advanced"))
outer.pack_start(book, True, True, 0)
win.add(outer); win.set_size_request(420, 470); win.show_all()
def shoot():
    pb = win.get_pixbuf(); pb.savev(out, "png", [], []); Gtk.main_quit(); return False
GLib.timeout_add(600, shoot); Gtk.main()
