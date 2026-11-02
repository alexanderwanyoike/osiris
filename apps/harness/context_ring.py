"""The context ring (#169): how full the Conversation's context window is, with
its share in the middle, in the accent until it nears full and then turning
to the danger colour (osiris.harness.context says when)."""
import math

import cairo
import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402

from osiris.harness.context import alarm, filled  # noqa: E402
from osiris.harness.style import RingColours  # noqa: E402

SIZE = 64
LINE = 6


class ContextRing(Gtk.Overlay):
    def __init__(self):
        super().__init__(valign=Gtk.Align.CENTER)
        self.add_css_class("harness-context-ring")
        #: How full the window is, and the colour it is drawn in.
        self.share = 0.0
        self.colour: str | None = None
        self._alarm = 0.0
        self._colours: RingColours | None = None
        self._area = Gtk.DrawingArea(content_width=SIZE, content_height=SIZE)
        self._area.set_draw_func(self._draw)
        self.set_child(self._area)
        self.said = Gtk.Label(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.add_overlay(self.said)

    def restyle(self, colours: RingColours) -> None:
        self._colours = colours
        self._recolour()

    def show(self, used: int, window: int, said: str) -> None:
        self.share, self._alarm = filled(used, window), alarm(used, window)
        self.said.set_text(said)
        self._recolour()

    def _recolour(self) -> None:
        if self._colours is not None:
            self.colour = self._colours.at(self._alarm)
        self._area.queue_draw()

    def _draw(self, _area, cr, width: int, height: int) -> None:
        if self._colours is None or self.colour is None:
            return
        radius = (min(width, height) - LINE) / 2
        cr.set_line_width(LINE)
        cr.set_line_cap(cairo.LineCap.ROUND)
        _source(cr, self._colours.track)
        cr.arc(width / 2, height / 2, radius, 0, math.tau)
        cr.stroke()
        if self.share:
            _source(cr, self.colour)
            top = -math.pi / 2
            cr.arc(width / 2, height / 2, radius, top, top + self.share * math.tau)
            cr.stroke()


def _source(cr, colour: str) -> None:
    rgba = Gdk.RGBA()
    rgba.parse(colour)
    cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, rgba.alpha)
