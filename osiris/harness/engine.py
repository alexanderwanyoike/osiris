"""The Engine port: what the Harness rents for model access and the agent loop.

The shape follows what opencode exposes (ADR 0015): sessions, prompts, a
stream of events, tool requests the client answers, and an interrupt. Another
Engine has to fit it.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ModelRef:
    provider: str
    model: str


@dataclass(frozen=True)
class Tokens:
    input: int
    output: int
    reasoning: int
    cache_read: int
    cache_write: int


@dataclass(frozen=True)
class Text:
    """A piece of the answer, as it streams."""

    session: str
    delta: str


@dataclass(frozen=True)
class ToolCalled:
    """The model called a tool, whether or not it was allowed to run."""

    session: str
    call: str
    input: dict[str, object]
    executed: bool


@dataclass(frozen=True)
class ToolRequested:
    """A tool waits for the Harness to allow or reject it."""

    session: str
    request: str
    action: str
    resources: tuple[str, ...]


@dataclass(frozen=True)
class Answered:
    """One step of the answer is complete, and this model gave it."""

    session: str
    model: ModelRef
    tokens: Tokens
    cost: float


@dataclass(frozen=True)
class Finished:
    session: str


@dataclass(frozen=True)
class Stopped:
    session: str


@dataclass(frozen=True)
class Failed:
    session: str
    message: str


Event = Text | ToolCalled | ToolRequested | Answered | Finished | Stopped | Failed


@dataclass(frozen=True)
class Past:
    """A Conversation the Harness had, as the Engine keeps it."""

    session: str
    title: str
    directory: Path
    #: Seconds since the epoch.
    updated: float


@dataclass(frozen=True)
class PastTurn:
    question: str
    answer: str
    model: ModelRef | None


@runtime_checkable
class Engine(Protocol):
    def start(
        self, model: ModelRef | None = None, directory: Path | None = None
    ) -> str:
        """Open a session and return its id; None leaves the Engine's default
        model, or its own folder."""
        ...

    def send(self, session: str, text: str) -> None: ...

    def events(self) -> Iterator[Event]:
        """Every session's events, for as long as the Engine runs."""
        ...

    def reply(self, session: str, request: str, *, allow: bool, message: str) -> None:
        """Answer a ``ToolRequested``; ``message`` is passed to the model."""
        ...

    def stop(self, session: str) -> None: ...

    def switch_model(self, session: str, model: ModelRef) -> None: ...

    def rename(self, session: str, title: str) -> None: ...

    def conversations(self) -> list[Past]:
        """The Harness's own sessions, newest first; other programs' are left out."""
        ...

    def history(self, session: str) -> list[PastTurn]: ...

    def attach_tools(self, name: str, command: list[str]) -> None:
        """Run a tool server for every session; each of its tools still raises
        a ``ToolRequested`` before it runs."""
        ...

    def action(self, server: str, tool: str) -> str:
        """The action a ``ToolRequested`` names for one of a tool server's tools."""
        ...
