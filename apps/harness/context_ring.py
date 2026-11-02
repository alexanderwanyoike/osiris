"""The context ring (#169): how full the Conversation's context window is, in
the accent until it nears full and then turning to the danger colour
(osiris.harness.context says when). It leads the Context card's header, so
it shows with the card folded."""
import math

import cairo
import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402

from osiris.harness.context import alarm, filled  # noqa: E402
from osiris.harness.style import RingColours  # noqa: E402

#: The size of the header's icons, which it stands among.
SIZE = 16
LINE = 3
#: How far the fill's glow spreads past its line, and how strong each step of
#: it is, the more so the nearer the window is to full.
GLOW = 3
GLOW_ALPHA = 0.14
GLOW_ALARM = 0.12


class ContextRing(Gtk.DrawingArea):
    def __init__(self):
        super().__init__(content_width=SIZE + 2 * GLOW,
                         content_height=SIZE + 2 * GLOW, valign=Gtk.Align.CENTER)
        self.add_css_class("harness-context-ring")
        #: How full the window is, and the colour it is drawn in.
        self.share = 0.0
        self.colour: str | None = None
        self._alarm = 0.0
        self._colours: RingColours | None = None
        self.set_draw_func(self._draw)

    def restyle(self, colours: RingColours) -> None:
        self._colours = colours
        self._recolour()

    def show(self, used: int, window: int) -> None:
        self.share, self._alarm = filled(used, window), alarm(used, window)
        self._recolour()

    def _recolour(self) -> None:
        if self._colours is not None:
            self.colour = self._colours.at(self._alarm)
        self.queue_draw()

    def _draw(self, _area, cr, width: int, height: int) -> None:
        if self._colours is None or self.colour is None:
            return
        x, y, radius = width / 2, height / 2, (SIZE - LINE) / 2
        cr.set_line_cap(cairo.LineCap.ROUND)
        cr.set_line_width(LINE)
        _source(cr, self._colours.track)
        cr.arc(x, y, radius, 0, math.tau)
        cr.stroke()
        if not self.share:
            return
        top = -math.pi / 2
        end = top + self.share * math.tau
        strength = GLOW_ALPHA + GLOW_ALARM * self._alarm
        for spread in range(GLOW, 0, -1):
            _source(cr, self.colour, strength)
            cr.set_line_width(LINE + 2 * spread)
            cr.arc(x, y, radius, top, end)
            cr.stroke()
        _source(cr, self.colour)
        cr.set_line_width(LINE)
        cr.arc(x, y, radius, top, end)
        cr.stroke()


def _source(cr, colour: str, alpha: float = 1.0) -> None:
    rgba = Gdk.RGBA()
    rgba.parse(colour)
    cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, alpha)
