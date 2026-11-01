"""The Conversation rail (#167): a slim strip at the Conversation's edge with a
tick per question, evenly spaced in a centred column.

Which ticks are lit, current and tinted, and where the column stands, are
decided in osiris/harness/rail.py; this lays the ticks out, grows the one
pointed at and its neighbours, shows its card, and passes on a click.
"""
from collections.abc import Callable

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gsk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Graphene, Gsk, Gtk  # noqa: E402

from osiris.harness.rail import Tick, column  # noqa: E402

#: The strip's width, which is each tick's reach for the pointer (WCAG 2.5.8
#: asks 24px of a target).
WIDTH = 24
#: Neighbours either side of the tick pointed at that grow with it.
NEAR = 2


class Rail(Gtk.Widget):
    __gtype_name__ = "HarnessRail"

    def __init__(self, on_jump: Callable[[int], None]):
        super().__init__(vexpand=True)
        self.add_css_class("harness-rail")
        self._on_jump = on_jump
        self._ticks: list[Tick] = []
        self._marks: list[Gtk.Widget] = []
        pointer = Gtk.EventControllerMotion()
        pointer.connect("motion", self.pointed)
        pointer.connect("leave", lambda _c: self._left())
        self.add_controller(pointer)
        self._place = Gtk.Label(xalign=0)
        self._place.add_css_class("harness-meta")
        self._question = Gtk.Label(xalign=0, wrap=True, max_width_chars=36, lines=2)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.append(self._place)
        card.append(self._question)
        # Without autohide the card leaves the pointer and keyboard where they
        # are, so moving down the rail moves it along.
        self.card = Gtk.Popover(child=card, autohide=False, has_arrow=False,
                                position=Gtk.PositionType.LEFT, can_focus=False)
        self.card.add_css_class("harness-rail-card")
        self.card.set_parent(self)

    def show_ticks(self, ticks: list[Tick]) -> None:
        # Scrolling changes only which are lit, so marks are kept and restyled
        # rather than made again.
        while len(self._marks) > len(ticks):
            self._marks.pop().unparent()
        while len(self._marks) < len(ticks):
            self._marks.append(self._mark(len(self._marks)))
        for mark, tick in zip(self._marks, ticks):
            near = [c for c in mark.get_css_classes() if c.startswith("near-")]
            mark.set_css_classes(["harness-rail-tick", tick.tone, *near,
                                  *(["lit"] if tick.lit else []),
                                  *(["current"] if tick.current else [])])
        self._ticks = list(ticks)
        self.queue_allocate()

    def _mark(self, index: int) -> Gtk.Widget:
        mark = Gtk.Box()
        line = Gtk.Box(valign=Gtk.Align.CENTER, halign=Gtk.Align.END, hexpand=True)
        line.add_css_class("harness-rail-line")
        mark.append(line)
        click = Gtk.GestureClick()
        click.connect("released", lambda *_args: self._on_jump(index))
        mark.add_controller(click)
        mark.set_parent(self)
        return mark

    def _at(self, y: float) -> int | None:
        """The tick at a point on the rail, if any."""
        if not self._marks:
            return None
        start, pitch = column(len(self._marks), self.get_height())
        index = int((y - start) // pitch)
        return index if 0 <= index < len(self._marks) else None

    def pointed(self, _controller, _x: float, y: float) -> None:
        index = self._at(y)
        if index is None:
            self._left()
            return
        for at, mark in enumerate(self._marks):
            for step in range(NEAR + 1):
                if abs(at - index) == step:
                    mark.add_css_class(f"near-{step}")
                else:
                    mark.remove_css_class(f"near-{step}")
        self._place.set_text(f"{index + 1} of {len(self._marks)}")
        self._question.set_text(self._ticks[index].label)
        start, pitch = column(len(self._marks), self.get_height())
        point = Gdk.Rectangle()
        point.x, point.y = 0, round(start + index * pitch)
        point.width, point.height = WIDTH, max(round(pitch), 1)
        self.card.set_pointing_to(point)
        self.card.popup()

    def _left(self) -> None:
        for mark in self._marks:
            for step in range(NEAR + 1):
                mark.remove_css_class(f"near-{step}")
        self.card.popdown()

    def do_measure(self, orientation, _for_size):
        if orientation == Gtk.Orientation.HORIZONTAL:
            return WIDTH, WIDTH, -1, -1
        return 0, 0, -1, -1

    def do_size_allocate(self, width, height, _baseline):
        start, pitch = column(len(self._marks), height)
        for index, mark in enumerate(self._marks):
            down = Graphene.Point().init(0, start + index * pitch)
            mark.allocate(width, max(round(pitch), 1), -1,
                          Gsk.Transform().translate(down))
        self.card.present()

    def do_dispose(self):
        for mark in self._marks:
            mark.unparent()
        self._marks = []
        self.card.unparent()
