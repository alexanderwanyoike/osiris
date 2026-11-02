"""The Conversation rail (#167), as the person sees and uses it."""

from __future__ import annotations

from osiris.harness.rail import Tick

from .conftest import texts

TICKS = [
    Tick(0.0, False, "plain", "what is a theme?"),
    Tick(0.5, True, "changed", "make it calm", current=True),
    Tick(0.9, True, "waiting", "list /etc"),
]


def _point():
    from gi.repository import Graphene

    return Graphene.Point()


def rail(jumped: list[int] | None = None):
    from rail import Rail

    shown = Rail(on_jump=(jumped if jumped is not None else []).append)
    shown.show_ticks(TICKS)
    return shown


def marks(shown) -> list[object]:
    found, child = [], shown.get_first_child()
    while child is not None:
        if child.has_css_class("harness-rail-tick"):
            found.append(child)
        child = child.get_next_sibling()
    return found


def test_each_question_has_a_tick_lit_and_tinted_and_the_first_on_screen_current() -> (
    None
):
    shown = marks(rail())
    assert [m.has_css_class("lit") for m in shown] == [False, True, True]
    assert [m.has_css_class("changed") for m in shown] == [False, True, False]
    assert shown[2].has_css_class("waiting")
    assert [m.has_css_class("current") for m in shown] == [False, True, False]


def test_pointing_at_a_tick_shows_its_place_and_how_its_question_starts() -> None:
    from gi.repository import Gtk

    from .test_composer_picker import settle

    shown = rail()
    window = Gtk.Window(child=shown, default_height=400)
    window.present()
    settle()
    middle = marks(shown)[1]
    shown.pointed(None, 4, middle.compute_point(shown, _point())[1].y + 2)
    words = texts(shown.card)
    visible = shown.card.get_visible()
    grown = [m.has_css_class("near-0") for m in marks(shown)]
    window.destroy()
    assert visible
    assert "2 of 3" in words and "make it calm" in words
    assert grown == [False, True, False]


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


def test_ticks_stand_evenly_in_a_column_centred_on_the_rail() -> None:
    from gi.repository import Graphene, Gtk

    from osiris.harness.rail import column

    from .test_composer_picker import settle

    shown = rail()
    window = Gtk.Window(child=shown, default_height=400)
    window.present()
    settle()
    tops = [mark.compute_point(shown, Graphene.Point())[1].y for mark in marks(shown)]
    window.destroy()
    start, pitch = column(3, 400)
    assert tops == [start, start + pitch, start + 2 * pitch]
