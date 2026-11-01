"""The Conversation rail (#167), as the person sees and uses it."""

from __future__ import annotations

from osiris.harness.rail import Tick

TICKS = [
    Tick(0.0, False, "plain", "what is a theme?"),
    Tick(0.5, True, "changed", "make it calm"),
    Tick(0.9, True, "waiting", "list /etc"),
]


def rail(jumped: list[int] | None = None):
    from rail import Rail

    shown = Rail(on_jump=(jumped if jumped is not None else []).append)
    shown.show_ticks(TICKS)
    return shown


def marks(shown) -> list[object]:
    found, child = [], shown.get_first_child()
    while child is not None:
        found.append(child)
        child = child.get_next_sibling()
    return found


def test_each_question_has_a_tick_lit_and_tinted_with_its_start_on_hover() -> None:
    shown = marks(rail())
    assert [m.get_tooltip_text() for m in shown] == [t.label for t in TICKS]
    assert [m.has_css_class("lit") for m in shown] == [False, True, True]
    assert [m.has_css_class("changed") for m in shown] == [False, True, False]
    assert shown[2].has_css_class("waiting")


def test_clicking_a_tick_jumps_to_its_question() -> None:
    jumped: list[int] = []
    shown = marks(rail(jumped))
    click = next(
        c
        for c in shown[1].observe_controllers()
        if c.__class__.__name__ == "GestureClick"
    )
    click.emit("released", 1, 4.0, 4.0)
    assert jumped == [1]


def test_ticks_stand_down_the_rail_where_their_questions_do() -> None:
    from gi.repository import Graphene, Gtk

    from .test_composer_picker import settle

    shown = rail()
    window = Gtk.Window(child=shown, default_height=409)
    window.present()
    settle()
    tops = [mark.compute_point(shown, Graphene.Point())[1].y for mark in marks(shown)]
    window.destroy()
    assert tops == [0, 200, 360]


def test_a_band_marks_the_part_on_screen() -> None:
    from gi.repository import Graphene, Gtk

    from .test_composer_picker import settle

    shown = rail()
    shown.show_view(0.25, 0.5)
    window = Gtk.Window(child=shown, default_height=400)
    window.present()
    settle()
    band = shown.band
    top = band.compute_point(shown, Graphene.Point())[1].y
    height = band.get_height()
    window.destroy()
    assert (top, height) == (100, 200)
