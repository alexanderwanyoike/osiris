"""The Harness: one session, a log of everything, and actions by tier."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from osiris.harness.engine import (
    Answered,
    Event,
    Failed,
    ModelRef,
    Past,
    PastTurn,
    Stopped,
    Text,
    Tokens,
    ToolCalled,
    ToolRequested,
)
from osiris.harness.harness import REFUSED, Allowed, Harness, Refused
from osiris.harness.log import LOG_FILE, HarnessLog
from osiris.harness.tiers import Tier
from osiris.platform import FakeFileSystem

HOME = Path("/home/tester")
NOON = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
GPT = ModelRef("openai", "gpt-5.5")
TOKENS = Tokens(input=10, output=4, reasoning=2, cache_read=0, cache_write=0)


@dataclass
class FakeEngine:
    started: list[ModelRef | None] = field(default_factory=list)
    directories: list[Path | None] = field(default_factory=list)
    sent: list[tuple[str, str]] = field(default_factory=list)
    replies: list[tuple[str, str, bool, str]] = field(default_factory=list)
    stopped: list[str] = field(default_factory=list)
    switched: list[tuple[str, ModelRef]] = field(default_factory=list)
    renamed: list[tuple[str, str]] = field(default_factory=list)
    moved: list[tuple[str, Path]] = field(default_factory=list)
    past: list[PastTurn] = field(default_factory=list)

    def start(
        self, model: ModelRef | None = None, directory: Path | None = None
    ) -> str:
        self.started.append(model)
        self.directories.append(directory)
        return f"ses_{len(self.started)}"

    def send(self, session: str, text: str) -> None:
        self.sent.append((session, text))

    def events(self) -> Iterator[Event]:
        return iter(())

    def reply(self, session: str, request: str, *, allow: bool, message: str) -> None:
        self.replies.append((session, request, allow, message))

    def stop(self, session: str) -> None:
        self.stopped.append(session)

    def switch_model(self, session: str, model: ModelRef) -> None:
        self.switched.append((session, model))

    def rename(self, session: str, title: str) -> None:
        self.renamed.append((session, title))

    def move(self, session: str, directory: Path) -> None:
        self.moved.append((session, directory))

    def history(self, session: str) -> list[PastTurn]:
        return self.past

    def conversations(self) -> list[Past]:
        return [Past("ses_1", "hello", HOME, 1.0)]


POMODORO = HOME / "Code" / "pomodoro"


def harness(
    model: ModelRef | None = GPT, tiers: dict[str, Tier] | None = None
) -> tuple[Harness, FakeEngine, FakeFileSystem]:
    engine, files = FakeEngine(), FakeFileSystem()
    log = HarnessLog(files, HOME / LOG_FILE, clock=lambda: NOON)
    subject = Harness(
        engine,
        log,
        model,
        tiers=tiers or {},
        directory=HOME,
        may_touch=lambda path: path == POMODORO or POMODORO in path.parents,
    )
    return subject, engine, files


def entries(files: FakeFileSystem) -> list[dict[str, object]]:
    return [json.loads(line) for line in files.read(HOME / LOG_FILE).splitlines()]


def test_the_first_question_opens_a_session_with_the_chosen_model() -> None:
    subject, engine, _ = harness()
    subject.ask("hello")
    assert engine.started == [GPT]
    assert engine.sent == [("ses_1", "hello")]


def test_later_questions_continue_the_same_conversation() -> None:
    subject, engine, _ = harness()
    subject.ask("hello")
    subject.ask("and again")
    assert engine.started == [GPT]
    assert engine.sent == [("ses_1", "hello"), ("ses_1", "and again")]


def test_the_session_starts_in_the_harnesss_folder() -> None:
    subject, engine, _ = harness()
    subject.ask("hello")
    assert engine.directories == [HOME]


def test_without_a_chosen_model_the_engine_default_is_used() -> None:
    subject, engine, _ = harness(model=None)
    subject.ask("hello")
    assert engine.started == [None]


def test_what_is_sent_is_logged_with_the_time() -> None:
    subject, _, files = harness()
    subject.ask("hello")
    assert entries(files) == [
        {
            "time": "2026-10-17T12:00:00+00:00",
            "kind": "sent",
            "session": "ses_1",
            "text": "hello",
        }
    ]


def test_an_answer_is_logged_with_the_model_that_gave_it() -> None:
    subject, _, files = harness()
    subject.ask("hello")
    subject.handle(Answered("ses_1", GPT, TOKENS, cost=0.0))
    entry = entries(files)[-1]
    assert entry["kind"] == "answered"
    assert entry["provider"] == "openai"
    assert entry["model"] == "gpt-5.5"
    assert entry["tokens"] == {
        "input": 10,
        "output": 4,
        "reasoning": 2,
        "cache_read": 0,
        "cache_write": 0,
    }


def test_an_action_without_a_tier_is_rejected_and_logged() -> None:
    subject, engine, files = harness()
    subject.ask("hello")
    subject.handle(ToolRequested("ses_1", "per_1", "shell", ("ls /etc",)))
    assert engine.replies == [("ses_1", "per_1", False, REFUSED)]
    entry = entries(files)[-1]
    assert entry["kind"] == "rejected"
    assert entry["action"] == "shell"
    assert entry["resources"] == ["ls /etc"]


@pytest.mark.parametrize("tier", [Tier.LOOK, Tier.UNDOABLE])
def test_an_action_with_a_tier_is_allowed_and_logged_with_it(tier: Tier) -> None:
    subject, engine, files = harness(tiers={"osiris_apply_theme": tier})
    subject.ask("make it calm")
    subject.handle(ToolRequested("ses_1", "per_1", "osiris_apply_theme", ("*",)))
    assert engine.replies == [("ses_1", "per_1", True, "")]
    entry = entries(files)[-1]
    assert entry["kind"] == "allowed"
    assert entry["action"] == "osiris_apply_theme"
    assert entry["tier"] == tier.value


def test_the_decision_is_passed_on_in_place_of_the_request() -> None:
    subject, _, _ = harness(tiers={"osiris_apply_theme": Tier.UNDOABLE})
    subject.ask("make it calm")
    allowed = subject.handle(
        ToolRequested("ses_1", "per_1", "osiris_apply_theme", ("*",))
    )
    refused = subject.handle(ToolRequested("ses_1", "per_2", "bash", ("ls",)))
    assert allowed == Allowed("ses_1", "osiris_apply_theme", Tier.UNDOABLE)
    assert refused == Refused("ses_1", "bash", ("ls",))


def test_a_rejection_points_the_model_at_the_tools_it_may_use() -> None:
    assert "Osiris tools" in REFUSED
    assert "only talk" not in REFUSED


def test_every_tool_call_is_logged_even_one_that_never_asked() -> None:
    subject, _, files = harness()
    subject.ask("hello")
    subject.handle(ToolCalled("ses_1", "call_1", {"query": "x"}, executed=True))
    entry = entries(files)[-1]
    assert entry["kind"] == "tool"
    assert entry["input"] == {"query": "x"}
    assert entry["executed"] is True


def test_a_failure_is_logged_with_its_reason() -> None:
    subject, _, files = harness()
    subject.ask("hello")
    subject.handle(Failed("ses_1", "no account connected"))
    entry = entries(files)[-1]
    assert entry["kind"] == "failed"
    assert entry["message"] == "no account connected"


def test_streamed_text_is_passed_on_but_not_logged_piece_by_piece() -> None:
    subject, _, files = harness()
    subject.ask("hello")
    event = Text("ses_1", "hel")
    assert subject.handle(event) is event
    assert [entry["kind"] for entry in entries(files)] == ["sent"]


def test_stopping_interrupts_the_conversation_and_is_logged() -> None:
    subject, engine, files = harness()
    subject.ask("hello")
    subject.stop()
    assert engine.stopped == ["ses_1"]
    subject.handle(Stopped("ses_1"))
    assert [entry["kind"] for entry in entries(files)] == ["sent", "stopped"]


def test_stopping_before_anything_was_asked_does_nothing() -> None:
    subject, engine, _ = harness()
    subject.stop()
    assert engine.stopped == []


def test_another_programs_sessions_are_left_alone() -> None:
    """opencode's event stream carries every session on the service, including
    ones its own terminal app opened. The Harness must not answer or log them."""
    subject, engine, files = harness()
    subject.ask("hello")
    elsewhere = ToolRequested("ses_tui", "per_9", "shell", ("make",))
    assert subject.handle(elsewhere) is None
    subject.handle(Answered("ses_tui", GPT, TOKENS, cost=0.0))
    assert engine.replies == []
    assert [entry["kind"] for entry in entries(files)] == ["sent"]


def test_before_anything_is_asked_no_session_is_the_harnesss() -> None:
    subject, engine, files = harness()
    assert subject.handle(ToolRequested("ses_tui", "per_9", "shell", ())) is None
    assert engine.replies == []
    assert not files.exists(HOME / LOG_FILE)


def test_a_new_model_before_any_question_opens_the_session_on_it() -> None:
    subject, engine, _ = harness(model=None)
    subject.use_model(GPT)
    subject.ask("hello")
    assert engine.started == [GPT]
    assert engine.switched == []


def test_a_new_model_mid_conversation_switches_the_open_session() -> None:
    subject, engine, _ = harness(model=None)
    subject.ask("hello")
    subject.use_model(GPT)
    assert engine.switched == [("ses_1", GPT)]


@pytest.mark.parametrize(
    ("action", "resources", "tier"),
    [
        ("read", ("Code/pomodoro/main.py",), Tier.LOOK),
        (
            "edit",
            ("Code/pomodoro/main.py", "Code/pomodoro/ui/window.py"),
            Tier.UNDOABLE,
        ),
        ("external_directory", (f"{POMODORO}/*",), Tier.LOOK),
        ("read", (f"{POMODORO}/README.md",), Tier.LOOK),
    ],
)
def test_files_inside_a_program_may_be_read_and_edited(
    action: str, resources: tuple[str, ...], tier: Tier
) -> None:
    subject, engine, _ = harness()
    subject.ask("add a pause button")
    decision = subject.handle(ToolRequested("ses_1", "per_1", action, resources))
    assert decision == Allowed("ses_1", action, tier)
    assert engine.replies == [("ses_1", "per_1", True, "")]


@pytest.mark.parametrize(
    ("action", "resources"),
    [
        ("read", (".ssh/id_ed25519",)),
        ("read", ("Code/pomodoro/../../.ssh/id_ed25519",)),
        ("edit", ("Code/pomodoro/main.py", ".bashrc")),
        ("external_directory", ("/etc/*",)),
        ("edit", ("Code/pomodoro-evil/main.py",)),
        ("bash", ("Code/pomodoro",)),
    ],
)
def test_files_anywhere_else_are_refused(
    action: str, resources: tuple[str, ...]
) -> None:
    subject, engine, _ = harness()
    subject.ask("add a pause button")
    subject.handle(ToolRequested("ses_1", "per_1", action, resources))
    assert engine.replies == [("ses_1", "per_1", False, REFUSED)]


def test_a_new_conversation_opens_a_new_session_on_its_first_question() -> None:
    subject, engine, _ = harness()
    subject.ask("hello")
    subject.new_conversation()
    subject.ask("something else")
    assert engine.started == [GPT, GPT]
    assert engine.sent == [("ses_1", "hello"), ("ses_2", "something else")]


def test_after_a_new_conversation_the_old_sessions_events_are_left_alone() -> None:
    subject, _, _ = harness()
    subject.ask("hello")
    subject.new_conversation()
    assert subject.handle(Text("ses_1", "late text")) is None


def test_the_first_question_names_the_session() -> None:
    subject, engine, _ = harness()
    subject.ask("Make me a calm theme\nfor working late")
    subject.ask("now warmer")
    assert engine.renamed == [("ses_1", "Make me a calm theme")]


def test_a_past_conversation_is_resumed_in_its_own_session() -> None:
    subject, engine, _ = harness()
    engine.past = [PastTurn("make a timer", "Made it.", GPT)]
    assert subject.resume("ses_9") == engine.past
    subject.ask("add a pause button")
    assert engine.started == []
    assert engine.sent == [("ses_9", "add a pause button")]
    assert subject.handle(Text("ses_9", "Done")) == Text("ses_9", "Done")


def test_the_harness_names_its_past_conversations() -> None:
    subject, _, _ = harness()
    assert subject.conversations() == [Past("ses_1", "hello", HOME, 1.0)]


def test_the_session_on_screen_is_known_once_something_is_asked() -> None:
    subject, _, _ = harness()
    assert subject.session is None
    subject.ask("hello")
    assert subject.session == "ses_1"


def test_a_conversation_with_no_project_takes_its_programs_project() -> None:
    subject, engine, _ = harness()
    subject.ask("build me a timer")
    subject.worked_on(POMODORO)
    assert engine.moved == [("ses_1", POMODORO)]
    subject.handle(ToolRequested("ses_1", "per_1", "read", ("main.py",)))
    assert engine.replies[-1][2] is True


def test_a_conversation_in_a_project_stays_there() -> None:
    subject, engine, _ = harness()
    subject.ask("build me a timer")
    subject.worked_on(POMODORO)
    subject.worked_on(HOME / "Code" / "notes")
    assert engine.moved == [("ses_1", POMODORO)]


def test_a_past_conversation_can_be_moved_into_a_project() -> None:
    subject, engine, _ = harness()
    subject.move("ses_old", POMODORO)
    assert engine.moved == [("ses_old", POMODORO)]
