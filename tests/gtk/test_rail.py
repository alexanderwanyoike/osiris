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
