"""The Harness: one session, a log of everything, and talking only."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from osiris.harness.engine import (
    Answered,
    Event,
    Failed,
    ModelRef,
    Stopped,
    Text,
    Tokens,
    ToolCalled,
    ToolRequested,
)
from osiris.harness.harness import TALK_ONLY, Harness
from osiris.harness.log import LOG_FILE, HarnessLog
from osiris.platform import FakeFileSystem

HOME = Path("/home/tester")
NOON = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
GPT = ModelRef("openai", "gpt-5.5")
TOKENS = Tokens(input=10, output=4, reasoning=2, cache_read=0, cache_write=0)


@dataclass
class FakeEngine:
    started: list[ModelRef | None] = field(default_factory=list)
    sent: list[tuple[str, str]] = field(default_factory=list)
    replies: list[tuple[str, str, bool, str]] = field(default_factory=list)
    stopped: list[str] = field(default_factory=list)

    def start(self, model: ModelRef | None = None) -> str:
        self.started.append(model)
        return f"ses_{len(self.started)}"

    def send(self, session: str, text: str) -> None:
        self.sent.append((session, text))

    def events(self) -> Iterator[Event]:
        return iter(())

    def reply(self, session: str, request: str, *, allow: bool, message: str) -> None:
        self.replies.append((session, request, allow, message))

    def stop(self, session: str) -> None:
        self.stopped.append(session)


def harness(
    model: ModelRef | None = GPT,
) -> tuple[Harness, FakeEngine, FakeFileSystem]:
    engine, files = FakeEngine(), FakeFileSystem()
    log = HarnessLog(files, HOME / LOG_FILE, clock=lambda: NOON)
    return Harness(engine, log, model), engine, files


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
    subject.handle(Answered("ses_1", GPT, TOKENS, cost=0.0))
    (entry,) = entries(files)
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


def test_every_tool_request_is_rejected_because_the_harness_only_talks() -> None:
    subject, engine, files = harness()
    subject.handle(ToolRequested("ses_1", "per_1", "shell", ("ls /etc",)))
    assert engine.replies == [("ses_1", "per_1", False, TALK_ONLY)]
    (entry,) = entries(files)
    assert entry["kind"] == "rejected"
    assert entry["action"] == "shell"
    assert entry["resources"] == ["ls /etc"]


def test_every_tool_call_is_logged_even_one_that_never_asked() -> None:
    subject, _, files = harness()
    subject.handle(ToolCalled("ses_1", "call_1", {"query": "x"}, executed=True))
    (entry,) = entries(files)
    assert entry["kind"] == "tool"
    assert entry["input"] == {"query": "x"}
    assert entry["executed"] is True


def test_a_failure_is_logged_with_its_reason() -> None:
    subject, _, files = harness()
    subject.handle(Failed("ses_1", "no account connected"))
    (entry,) = entries(files)
    assert entry["kind"] == "failed"
    assert entry["message"] == "no account connected"


def test_streamed_text_is_passed_on_but_not_logged_piece_by_piece() -> None:
    subject, _, files = harness()
    event = Text("ses_1", "hel")
    assert subject.handle(event) is event
    assert not files.exists(HOME / LOG_FILE)


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
