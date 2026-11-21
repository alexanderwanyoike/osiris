"""The mark leading a Provider or a model: its logo where Osiris ships one,
else a monogram of its name (apps/harness/logos)."""
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402


def badge(icon: str | None, name: str, size: int) -> Gtk.Widget:
    if icon is not None:
        logo = Gtk.Image(icon_name=icon, pixel_size=size)
        logo.add_css_class("harness-logo")
        return logo
    monogram = Gtk.Label(label=name[:1].upper())
    monogram.add_css_class("harness-monogram")
    return monogram
