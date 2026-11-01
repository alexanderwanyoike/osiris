"""The Conversation rail (#167): a thin strip at the Conversation's edge with a
tick per question.

Where each tick stands, whether it is lit and how it is tinted are decided in
osiris/harness/rail.py; this lays the ticks down the strip and passes on a
click.
"""
from collections.abc import Callable

import gi

gi.require_version("Gsk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Graphene, Gsk, Gtk  # noqa: E402

from osiris.harness.rail import Tick  # noqa: E402

#: The strip's width, which is also each tick's.
WIDTH = 14
#: A tick's height to point at; the line drawn inside it is thinner.
REACH = 9


class Rail(Gtk.Widget):
    __gtype_name__ = "HarnessRail"

    def __init__(self, on_jump: Callable[[int], None]):
        super().__init__(vexpand=True)
        self.add_css_class("harness-rail")
        self._on_jump = on_jump
        self._ticks: list[Tick] = []
        self._marks: list[Gtk.Widget] = []

    def show_ticks(self, ticks: list[Tick]) -> None:
        for mark in self._marks:
            mark.unparent()
        self._ticks, self._marks = list(ticks), []
        for index, tick in enumerate(ticks):
            self._marks.append(self._mark(index, tick))
        self.queue_allocate()

    def _mark(self, index: int, tick: Tick) -> Gtk.Widget:
        mark = Gtk.Box(height_request=REACH, tooltip_text=tick.label,
                       css_classes=["harness-rail-tick", tick.tone,
                                    *(["lit"] if tick.lit else [])])
        line = Gtk.Box(valign=Gtk.Align.CENTER, hexpand=True)
        line.add_css_class("harness-rail-line")
        mark.append(line)
        click = Gtk.GestureClick()
        click.connect("released", lambda *_args: self._on_jump(index))
        mark.add_controller(click)
        mark.set_parent(self)
        return mark

    def do_measure(self, orientation, _for_size):
        if orientation == Gtk.Orientation.HORIZONTAL:
            return WIDTH, WIDTH, -1, -1
        return 0, 0, -1, -1

    def do_size_allocate(self, width, height, _baseline):
        for tick, mark in zip(self._ticks, self._marks):
            # Down to the strip's foot, keeping the last tick wholly on it.
            down = round(tick.at * max(height - REACH, 0))
            place = Gsk.Transform().translate(Graphene.Point().init(0, down))
            mark.allocate(width, REACH, -1, place)

    def do_dispose(self):
        for mark in self._marks:
            mark.unparent()
        self._marks = []
