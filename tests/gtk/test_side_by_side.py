"""Conversations run side by side: the person can leave one while Osiris
answers it, and what it is still doing reaches it, not the one on screen."""

from __future__ import annotations

import time
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
        self.pages: list[str] = []
        self.refreshes = 0
        self.picker_refreshes = 0
        self.picker = SimpleNamespace(refresh=self._picker_refreshed)

    def _picker_refreshed(self) -> None:
        self.picker_refreshes += 1

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

    def open_page(self, at: str) -> None:
        self.pages.append(at)


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
        servers=None,
        saved=None,
        requests=None,
        files=files,
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
    context, deadline = GLib.MainContext.default(), time.monotonic() + 2
    while stand_in.histories == 0 and time.monotonic() < deadline:
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


def test_a_questions_changes_come_from_its_commits_and_a_comment_reaches_thoth() -> (
    None
):
    from osiris.harness.engine import FileChange
    from osiris.harness.log import Change
    from osiris.platform import FakeRunner
    from osiris.platform.process import Result
    from osiris.programs.programs import Programs

    patch = "diff --git a/main.py b/main.py\n@@ -1 +1 @@\n-a\n+b"
    runner = FakeRunner(
        results={
            f"git -C {HOME}/Code/coin-flip show --format= --patch abc": Result(
                (), 0, patch
            )
        }
    )
    stand_in, engine = app()
    stand_in.programs = lambda: Programs(FakeFileSystem(), runner, HOME)
    engine.past = [PastTurn("tidy main.py", "Tidied.", GPT, "msg_1")]
    stand_in.open_past("ses_9")
    turn = stand_in.conversation.turns[0]
    turn.changes.append(
        Change(
            "coin-flip: Tidy",
            {"action": "revert_commit", "name": "coin-flip", "commit": "abc"},
            "coin-flip",
        )
    )
    stand_in.show_changes(turn)
    question, files, on_comment = stand_in.drawer.changes[-1]
    assert (question, files) == (
        "tidy main.py",
        (FileChange("coin-flip/main.py", "modified", 1, 1, patch),),
    )
    on_comment("coin-flip/main.py", (3, 4), "Name it better.")
    assert stand_in.conversation.turns[-1].question == (
        "About coin-flip/main.py, lines 3 to 4:\n\nName it better."
    )


def test_changes_from_the_toolbar_open_each_questions_in_order_newest_last() -> None:
    """The newest, opened last, is the one on screen."""
    from osiris.harness.log import Change
    from osiris.platform import FakeRunner
    from osiris.platform.process import Result
    from osiris.programs.programs import Programs

    def show(commit: str) -> str:
        return f"git -C {HOME}/Code/coin-flip show --format= --patch {commit}"

    patch = "diff --git a/main.py b/main.py\n@@ -1 +1 @@\n-a\n+b"
    runner = FakeRunner(results={show(c): Result((), 0, patch) for c in ("aaa", "bbb")})
    stand_in, engine = app()
    stand_in.programs = lambda: Programs(FakeFileSystem(), runner, HOME)
    engine.past = [
        PastTurn("make a coin flip", "Made it.", GPT, "msg_1"),
        PastTurn("thanks", "You're welcome.", GPT, "msg_2"),
        PastTurn("add --times", "Added it.", GPT, "msg_3"),
    ]
    stand_in.open_past("ses_9")
    first, _, third = stand_in.conversation.turns
    for turn, commit in ((first, "aaa"), (third, "bbb")):
        turn.changes.append(
            Change(
                "coin-flip: change",
                {"action": "revert_commit", "name": "coin-flip", "commit": commit},
                "coin-flip",
            )
        )
    stand_in.show_all_changes()
    assert [question for question, _, _ in stand_in.drawer.changes] == [
        "make a coin flip",
        "add --times",
    ]


def test_changes_whose_program_is_gone_say_so_on_their_question() -> None:
    """As after an Undo trashed the Program the question made."""
    from osiris.harness.log import Change
    from osiris.platform import CommandError, FakeRunner
    from osiris.programs.programs import Programs

    show = f"git -C {HOME}/Code/coin-flip show --format= --patch abc"
    runner = FakeRunner(
        results={show: CommandError(tuple(show.split()), 128, "not a git repository")}
    )
    stand_in, engine = app()
    stand_in.programs = lambda: Programs(FakeFileSystem(), runner, HOME)
    engine.past = [PastTurn("make a coin flip", "Made it.", GPT, "msg_1")]
    stand_in.open_past("ses_9")
    turn = stand_in.conversation.turns[0]
    turn.changes.append(
        Change(
            "coin-flip: Add a flip",
            {"action": "revert_commit", "name": "coin-flip", "commit": "abc"},
            "coin-flip",
        )
    )
    stand_in.show_changes(turn)
    assert stand_in.drawer.changes == []
    assert "coin-flip" in turn.note


def test_a_page_thoth_reads_opens_in_the_browser_group() -> None:
    """So the person can follow its sources (#197)."""
    from osiris.harness.engine import ToolCalled

    stand_in, _ = app()
    asked(stand_in, "what is a GtkLabel?")
    page = "https://docs.gtk.org/gtk4/class.Label.html"
    heard(stand_in, ToolCalled("ses_1", "call_1", {"url": page}, False, "webfetch"))
    heard(stand_in, ToolCalled("ses_1", "call_2", {"path": "/etc/x"}, False, "read"))
    assert stand_in.drawer.pages == [page]


def test_a_message_sent_now_waits_shown_while_the_engine_cuts_in() -> None:
    stand_in, engine = app()
    asked(stand_in, "count to sixty")
    stand_in.send_now("stop, count to ten")
    assert engine.cut == ["ses_1"]
    assert [w.text for w in stand_in.conversation.waiting] == ["stop, count to ten"]


def test_commits_made_in_a_shell_are_among_a_questions_changes_when_it_ends() -> None:
    """#219: the model committed with git, not commit_program."""
    from osiris.harness.log import Change

    class History:
        def commits_since(self, name: str, _since: object) -> list[tuple[str, str]]:
            return [("abc123", "Track habits")] if name == "daily-habits" else []

        def label(self, _name: str) -> str:
            return "Daily Habits"

    stand_in, _ = app()
    stand_in.programs = History
    on_screen = asked(stand_in, "build me a habit tracker")
    stand_in.log.write(
        "changed",
        session="ses_1",
        summary="Made Daily Habits",
        undo={"action": "trash_program", "name": "daily-habits"},
        program="daily-habits",
    )
    heard(stand_in, Finished("ses_1"))
    assert on_screen.turns[-1].changes[-1] == Change(
        "Daily Habits: Track habits",
        {"action": "revert_commit", "name": "daily-habits", "commit": "abc123"},
        "daily-habits",
    )


def test_the_canvas_is_told_which_conversation_it_shows() -> None:
    """So each Conversation's Changes tabs go and come with it (#220)."""
    stand_in, _ = app()
    del stand_in.update_canvas
    shown: list[tuple[object, object]] = []
    stand_in.drawer.show_canvas = lambda found, conversation: shown.append(
        (found, conversation)
    )
    stand_in.drawer.conversation_panel = SimpleNamespace(get_mapped=lambda: False)
    stand_in.refresh_offers = lambda: None
    stand_in.programs = lambda: SimpleNamespace(programs=lambda: [])
    asked(stand_in, "build me a timer")
    stand_in.update_canvas()
    assert shown == [([], "ses_1")]


class Credits:
    """Programs' commits since a question, as git would give them."""

    def __init__(self, found: dict[str, list[tuple[str, str]]]) -> None:
        self.found = found

    def commits_since(self, name: str, _since: object) -> list[tuple[str, str]]:
        if name not in self.found:
            from osiris.platform.process import CommandError

            raise CommandError(["git", "log"], 128, f"{name} is gone")
        return self.found[name]

    def label(self, name: str) -> str:
        return name.title()


def test_an_answer_ending_off_screen_credits_the_program_it_runs_in() -> None:
    """Its Conversation was in the Program's Project all along (#219)."""
    stand_in, _ = app()
    stand_in.programs = lambda: Credits({"pomodoro": [("abc123", "Add a pause")]})
    asked(stand_in, "add a pause button")
    stand_in.new_conversation()
    heard(stand_in, Finished("ses_1"))
    summaries = [c.summary for c in stand_in.log.changes_by_question("ses_1")[-1]]
    assert summaries == ["Pomodoro: Add a pause"]


def test_a_gone_program_does_not_keep_the_others_from_being_credited() -> None:
    stand_in, _ = app()
    stand_in.programs = lambda: Credits({"pomodoro": [("abc123", "Add a pause")]})
    asked(stand_in, "tidy both")
    stand_in.log.write(
        "changed", session="ses_1", summary="Made Gone", undo=None, program="gone"
    )
    heard(stand_in, Finished("ses_1"))
    summaries = [c.summary for c in stand_in.log.changes_by_question("ses_1")[-1]]
    assert summaries == ["Made Gone", "Pomodoro: Add a pause"]


def test_a_question_asked_while_an_ended_answer_is_credited_keeps_its_own() -> None:
    """Crediting reads git off the main loop; the next question may be sent
    meanwhile, and the ended answer's changes are not that question's."""
    stand_in, _ = app()
    stand_in.programs = lambda: Credits({"pomodoro": [("abc123", "Add a pause")]})
    later: list[tuple[object, object]] = []
    stand_in.background = lambda work, done: later.append((work, done))
    asked(stand_in, "add a pause button")
    heard(stand_in, Finished("ses_1"))
    following = asked(stand_in, "and a reset button").turns[-1]
    for work, done in later:
        done(work())  # type: ignore[operator]
    assert following.changes == []
