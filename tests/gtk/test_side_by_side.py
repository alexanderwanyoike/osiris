"""Conversations run side by side: the person can leave one while Osiris
answers it, and what it is still doing reaches it, not the one on screen."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import main

from osiris.harness.conversation import Conversation
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
