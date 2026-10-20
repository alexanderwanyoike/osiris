"""A turn in the drawer: what its answer changed, and the Undo for it."""

from __future__ import annotations

import time
from collections.abc import Callable

from gi.repository import GLib, Gtk
from render import TurnView

from osiris.harness.activity import Step
from osiris.harness.admin import Request
from osiris.harness.conversation import State, Turn
from osiris.harness.log import Change
from osiris.harness.markdown import InlineStyle

from .conftest import find, shown, texts, widgets

STYLE = InlineStyle(code_foreground="#ffffff", code_background="#000000")
MADE = Change("Made Harbour", {"action": "delete_theme", "name": "harbour"})
APPLIED = Change("Applied Harbour", {"action": "apply_theme", "name": "nord"})


def drawn(
    turn: Turn,
    undone: list[Turn] | None = None,
    cards: list[str] | None = None,
    clock: Callable[[], float] = lambda: 0.0,
) -> TurnView:
    def card(name: str) -> Gtk.Widget:
        (cards if cards is not None else []).append(name)
        return Gtk.Label(label=f"card for {name}")

    view = TurnView(
        turn,
        on_undo=(undone if undone is not None else []).append,
        program_card=card,
        clock=clock,
    )
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


def test_a_turn_that_changed_programs_shows_a_card_for_each() -> None:
    cards: list[str] = []
    turn = finished(
        Change("Made Pomodoro", None, program="pomodoro"),
        Change("Made Notes", None, program="notes"),
    )
    view = drawn(turn, cards=cards)
    assert cards == ["pomodoro", "notes"]
    assert "card for pomodoro" in texts(view)


def test_a_working_turn_says_it_is_thinking_and_for_how_long() -> None:
    now = [100.0]
    turn = Turn("make a timer")
    view = drawn(turn, clock=lambda: now[0])
    now[0] = 114.0
    view.update(turn, STYLE, None)
    assert "Thinking" in shown(view)
    assert "14s" in shown(view)


def happens(condition: Callable[[], bool], within: float = 2.0) -> bool:
    """Whether condition comes true while the main loop runs, within seconds."""
    deadline = time.monotonic() + within
    while time.monotonic() < deadline:
        GLib.MainContext.default().iteration(False)
        if condition():
            return True
        time.sleep(0.01)
    return False


def test_the_time_counts_up_each_second_while_osiris_works() -> None:
    now = [100.0]
    view = drawn(Turn("make a timer"), clock=lambda: now[0])
    now[0] = 103.0
    assert happens(lambda: "3s" in shown(view))


def test_once_the_answer_ends_the_working_row_goes_and_stops_counting() -> None:
    turn = Turn("make a timer")
    view = drawn(turn)
    turn.state = State.DONE
    view.update(turn, STYLE, None)
    assert "Thinking" not in shown(view)
    assert not view.working.ticking


def test_what_osiris_did_is_kept_folded_under_the_answer() -> None:
    turn = finished()
    turn.steps = [
        Step("edit", ("pomodoro/main.py",)),
        Step("bash", ("ls /etc",), allowed=False),
    ]
    record = find(drawn(turn), Gtk.Expander)
    assert record.get_label() == "Used 2 tools"
    assert not record.get_expanded()
    steps = record.get_child()
    assert "Edited pomodoro/main.py" in texts(steps)
    assert "Not allowed to run ls /etc" in texts(steps)
    icons = [w.get_icon_name() for w in widgets(steps) if isinstance(w, Gtk.Image)]
    assert icons == ["object-select-symbolic", "changes-prevent-symbolic"]


def test_an_answer_that_took_no_steps_keeps_no_record() -> None:
    view = drawn(finished())
    assert not any(text.startswith("Used") for text in shown(view))


def test_a_command_waiting_for_the_password_shows_its_card_under_the_answer() -> None:
    asked: list[Request] = []
    card = Gtk.Label(label="admin card")

    def admin_card(request: Request) -> Gtk.Widget:
        asked.append(request)
        return card

    turn = Turn("install cowsay", "Installing.", State.ANSWERING)
    turn.admin = Request(("pacman", "-S", "cowsay"))
    view = TurnView(
        turn, on_undo=lambda _t: None, program_card=Gtk.Label, admin_card=admin_card
    )
    view.update(turn, STYLE, None)
    view.update(turn, STYLE, None)
    assert asked[-1] == turn.admin
    assert card.get_parent() is view.extras
    turn.admin = None
    view.update(turn, STYLE, None)
    assert "admin card" not in texts(view)
