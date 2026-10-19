"""Conversations run side by side: the person can leave one while Osiris
answers it, and what it is still doing reaches it, not the one on screen."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import main

from osiris.harness.conversation import Conversation
from osiris.harness.engine import Event, Finished, Text
from osiris.harness.harness import Harness
from osiris.harness.log import LOG_FILE, HarnessLog
from osiris.platform import FakeFileSystem
from tests.test_harness import GPT, HOME, FakeEngine

from .conftest import now


class FakeDrawer:
    def __init__(self) -> None:
        self.entry = SimpleNamespace(grab_focus=lambda: None)
        self.refreshes = 0

    def clear(self) -> None:
        pass

    def refresh(self, restyle: bool = False) -> None:
        self.refreshes += 1


class App(SimpleNamespace):
    """Stands in for the Application: its own methods, on plain state."""

    def __getattr__(self, name: str) -> Any:
        return getattr(main.Application, name).__get__(self)


def app() -> tuple[App, FakeEngine]:
    engine, files = FakeEngine(), FakeFileSystem()
    log = HarnessLog(files, HOME / LOG_FILE)
    harness = Harness(
        engine, log, GPT, tiers={}, directory=HOME, may_touch=lambda _path: False
    )
    stand_in = App(
        harness=harness,
        log=log,
        home=HOME,
        conversation=Conversation(),
        backgrounded={},
        drawer=FakeDrawer(),
        background=now,
        histories=0,
        canvases=0,
    )
    stand_in.load_history = lambda: setattr(
        stand_in, "histories", stand_in.histories + 1
    )
    stand_in.update_canvas = lambda: setattr(
        stand_in, "canvases", stand_in.canvases + 1
    )
    return stand_in, engine


def heard(stand_in: App, event: Event) -> None:
    """An event from the Engine, through the Harness to the main loop."""
    handled = stand_in.harness.handle(event)
    if handled is not None:
        stand_in._apply(handled)


def asked(stand_in: App, text: str) -> Conversation:
    """A question sent on the Conversation on screen, as the drawer sends it."""
    stand_in.conversation.asked(text)
    stand_in.harness.ask(text)
    return stand_in.conversation


def test_a_new_conversation_while_osiris_works_keeps_the_one_left_working() -> None:
    stand_in, _ = app()
    working = asked(stand_in, "make it calm")
    stand_in.new_conversation()
    assert stand_in.conversation is not working
    assert not stand_in.conversation.turns
    assert stand_in.backgrounded == {"ses_1": working}


def test_while_the_first_question_is_still_on_its_way_the_conversation_stays() -> None:
    """Until the Engine has opened its session there is nothing to keep it by,
    and nothing would reach it."""
    stand_in, _ = app()
    stand_in.conversation.asked("make it calm")
    sending = stand_in.conversation
    stand_in.new_conversation()
    assert stand_in.conversation is sending
    assert stand_in.backgrounded == {}


def test_what_osiris_still_says_off_screen_reaches_its_own_conversation() -> None:
    stand_in, _ = app()
    working = asked(stand_in, "make it calm")
    stand_in.new_conversation()
    asked(stand_in, "something else")
    heard(stand_in, Text("ses_1", "Calmer now."))
    assert working.turns[-1].answer == "Calmer now."
    assert stand_in.conversation.turns[-1].answer == ""


def test_a_conversation_ending_off_screen_is_let_go_and_leaves_the_screen_alone() -> (
    None
):
    """The history shows it from then on. What the log says changed belongs
    to the question on screen, so it is not put on that answer early."""
    stand_in, _ = app()
    asked(stand_in, "make it calm")
    stand_in.new_conversation()
    on_screen = asked(stand_in, "something else")
    stand_in.log.write("changed", summary="Applied Calm", undo={"theme": "nord"})
    histories, canvases = stand_in.histories, stand_in.canvases
    heard(stand_in, Finished("ses_1"))
    assert stand_in.backgrounded == {}
    assert on_screen.turns[-1].changes == []
    assert stand_in.canvases == canvases
    assert stand_in.histories > histories
