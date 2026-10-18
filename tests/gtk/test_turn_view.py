"""A turn in the drawer: what its answer changed, and the Undo for it."""

from __future__ import annotations

from gi.repository import Gtk
from render import TurnView

from osiris.harness.conversation import State, Turn
from osiris.harness.log import Change
from osiris.harness.markdown import InlineStyle

from .conftest import find, texts, widgets

STYLE = InlineStyle(code_foreground="#ffffff", code_background="#000000")
MADE = Change("Made Harbour", {"action": "delete_theme", "name": "harbour"})
APPLIED = Change("Applied Harbour", {"action": "apply_theme", "name": "nord"})


def drawn(turn: Turn, undone: list[Turn] | None = None) -> TurnView:
    view = TurnView(turn, on_undo=(undone if undone is not None else []).append)
    view.update(turn, STYLE, None)
    return view


def finished(*changes: Change) -> Turn:
    return Turn("make it calm", "Done.", State.DONE, changes=list(changes))


def test_a_turn_that_changed_something_says_what_and_offers_undo() -> None:
    undone: list[Turn] = []
    turn = finished(MADE, APPLIED)
    view = drawn(turn, undone)
    assert "Made Harbour  ·  Applied Harbour" in texts(view)
    find(view, Gtk.Button, "Undo").emit("clicked")
    assert undone == [turn]


def test_an_undone_turn_says_so_and_offers_no_undo() -> None:
    turn = finished(MADE)
    turn.undone = True
    view = drawn(turn)
    assert "Undone" in texts(view)
    assert not any(
        isinstance(w, Gtk.Button) and w.get_label() == "Undo" for w in widgets(view)
    )


def test_a_turn_that_changed_nothing_shows_no_changes() -> None:
    view = drawn(finished())
    assert not any("Undo" in text for text in texts(view))
