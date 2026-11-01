"""Conversations run side by side: the person can leave one while Osiris
answers it, and what it is still doing reaches it, not the one on screen."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import main

from osiris.harness.conversation import Conversation
from osiris.harness.engine import Event, Finished, PastTurn, Text
from osiris.harness.harness import Harness
from osiris.harness.log import LOG_FILE, HarnessLog
from osiris.harness.unread import Unread
from osiris.platform import FakeFileSystem
from tests.test_harness import GPT, HOME, FakeEngine

from .conftest import now


class FakeDrawer:
    def __init__(self) -> None:
        self.entry = SimpleNamespace(grab_focus=lambda: None)
        self.drafts: list[str] = []
        self.changes: list[tuple[str, object, Any]] = []
        self.refreshes = 0

    def clear(self) -> None:
        pass

    def refresh(self, restyle: bool = False) -> None:
        self.refreshes += 1

    def summon(self) -> None:
        pass

    def draft(self, text: str) -> None:
        self.drafts.append(text)

    def show_changes(self, question: str, files: object, on_comment: Any) -> None:
        self.changes.append((question, files, on_comment))


class App(SimpleNamespace):
    """Stands in for the Application: its own methods, on plain state."""

    def __getattr__(self, name: str) -> Any:
        return getattr(main.Application, name).__get__(self)


def app() -> tuple[App, FakeEngine]:
    engine, files = FakeEngine(), FakeFileSystem()
    log = HarnessLog(files, HOME / LOG_FILE)
    harness = Harness(engine, log, GPT, directory=HOME)
    stand_in = App(
        harness=harness,
        log=log,
        home=HOME,
        conversation=Conversation(),
        backgrounded={},
        admin_pending={},
        approvals={},
        drawer=FakeDrawer(),
        background=now,
        histories=0,
        canvases=0,
        open=True,
        unread=Unread(files, HOME),
        sent=[],
        withdrawn=[],
        waiting=None,
        problem=None,
    )
    stand_in.send_notification = lambda session, notification: stand_in.sent.append(
        (session, notification)
    )
    stand_in.withdraw_notification = stand_in.withdrawn.append
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


def test_a_past_conversation_can_be_opened_while_osiris_works() -> None:
    stand_in, engine = app()
    engine.past = [PastTurn("make a timer", "Made it.", GPT)]
    working = asked(stand_in, "make it calm")
    stand_in.open_past("ses_9")
    assert [turn.answer for turn in stand_in.conversation.turns] == ["Made it."]
    assert stand_in.backgrounded == {"ses_1": working}


def test_opening_a_conversation_still_working_shows_it_as_it_goes_on() -> None:
    """Its history at the Engine is only what was said so far; the live
    Conversation is what is still arriving."""
    stand_in, engine = app()
    engine.past = [PastTurn("make it calm", "", GPT)]
    working = asked(stand_in, "make it calm")
    stand_in.new_conversation()
    other = asked(stand_in, "something else")
    stand_in.open_past("ses_1")
    assert stand_in.conversation is working
    assert stand_in.backgrounded == {"ses_2": other}
    heard(stand_in, Text("ses_1", "Calmer now."))
    assert working.turns[-1].answer == "Calmer now."


def test_the_sidebar_is_refreshed_once_a_question_has_its_session_working() -> None:
    """So the new Conversation is listed, with its spinner."""
    from gi.repository import GLib

    stand_in, _ = app()
    stand_in.conversation.asked("make it calm")
    stand_in._send("make it calm")
    context = GLib.MainContext.default()
    for _ in range(50):
        context.iteration(False)
    assert stand_in.histories == 1


def test_a_conversation_deleted_while_working_off_screen_is_let_go() -> None:
    """The Engine erases it, so no end will ever come to let it go."""
    stand_in, _ = app()
    asked(stand_in, "make it calm")
    stand_in.new_conversation()
    stand_in.harness.delete("ses_1")
    stand_in._deleted("ses_1", on_screen=False)
    assert stand_in.backgrounded == {}


def test_going_back_reloads_the_conversation_and_puts_the_question_back() -> None:
    """As opencode's own undo does, so it can be sent again or changed."""
    stand_in, engine = app()
    engine.past = [
        PastTurn("make x.txt", "Made it.", GPT, "msg_1"),
        PastTurn("make y.txt", "Made it.", GPT, "msg_2"),
    ]
    stand_in.open_past("ses_9")
    engine.past = engine.past[:1]
    stand_in.go_back(stand_in.conversation.turns[1])
    assert engine.reverted == [("ses_9", "msg_2")]
    assert [turn.question for turn in stand_in.conversation.turns] == ["make x.txt"]
    assert stand_in.drawer.drafts == ["make y.txt"]


def test_where_the_files_cannot_go_back_the_person_is_told_and_nothing_moves() -> None:
    from osiris.harness.engine import Revert

    stand_in, engine = app()
    engine.past = [PastTurn("make x.txt", "Made it.", GPT, "msg_1")]
    stand_in.open_past("ses_9")
    engine.revert_gives = Revert((), restorable=False)
    stand_in.go_back(stand_in.conversation.turns[0])
    assert [turn.question for turn in stand_in.conversation.turns] == ["make x.txt"]
    assert "git" in stand_in.conversation.turns[0].note
    assert stand_in.drawer.drafts == []


def test_a_question_sent_now_names_its_message_so_it_can_be_gone_back_to() -> None:
    from gi.repository import GLib

    stand_in, _ = app()
    turn = stand_in.conversation.asked("make it calm")
    stand_in._send("make it calm", turn)
    context = GLib.MainContext.default()
    for _ in range(50):
        context.iteration(False)
    assert turn.message == "msg_1"


def test_an_engine_error_while_going_back_is_told_on_the_question() -> None:
    from osiris.platform import HttpError

    stand_in, engine = app()
    engine.past = [PastTurn("make x.txt", "Made it.", GPT, "msg_1")]
    stand_in.open_past("ses_9")

    def broken(*_args: object) -> None:
        raise HttpError(500, "snapshot store unavailable")

    engine.revert = broken
    stand_in.go_back(stand_in.conversation.turns[0])
    assert "snapshot store unavailable" in stand_in.conversation.turns[0].note


def test_trying_again_goes_back_then_sends_the_question_again() -> None:
    stand_in, engine = app()
    engine.past = [
        PastTurn("make x.txt", "Made it.", GPT, "msg_1"),
        PastTurn("make y.txt", "Made it.", GPT, "msg_2"),
    ]
    stand_in.open_past("ses_9")
    engine.past = engine.past[:1]
    stand_in.go_back(stand_in.conversation.turns[1], again=True)
    assert engine.reverted == [("ses_9", "msg_2")]
    assert [turn.question for turn in stand_in.conversation.turns] == [
        "make x.txt",
        "make y.txt",
    ]
    assert stand_in.drawer.drafts == []


def test_a_questions_changes_are_shown_and_a_comment_on_them_reaches_thoth() -> None:
    from osiris.harness.engine import FileChange

    stand_in, engine = app()
    engine.past = [PastTurn("tidy main.py", "Tidied.", GPT, "msg_1")]
    stand_in.open_past("ses_9")
    engine.changed = (FileChange("main.py", "modified", 1, 0, "+x\n"),)
    stand_in.show_changes(stand_in.conversation.turns[0])
    question, files, on_comment = stand_in.drawer.changes[-1]
    assert (question, files) == ("tidy main.py", engine.changed)
    on_comment("main.py", (3, 4), "Name it better.")
    assert stand_in.conversation.turns[-1].question == (
        "About main.py, lines 3 to 4:\n\nName it better."
    )


def test_a_message_sent_now_waits_shown_while_the_engine_cuts_in() -> None:
    stand_in, engine = app()
    asked(stand_in, "count to sixty")
    stand_in.send_now("stop, count to ten")
    assert engine.cut == ["ses_1"]
    assert [w.text for w in stand_in.conversation.waiting] == ["stop, count to ten"]
