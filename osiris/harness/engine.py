"""The Engine port: what the Harness rents for model access and the agent loop.

The shape follows what opencode exposes (ADR 0015): sessions, prompts, a
stream of events, tool requests the client answers, and an interrupt. Another
Engine has to fit it.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol, runtime_checkable


class Reply(Enum):
    """How a ``ToolRequested`` is answered."""

    ONCE = "once"
    #: Allowed, and the Engine keeps allowing what it suggests, in the Project.
    ALWAYS = "always"
    REJECT = "reject"


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
    #: The tool as the Engine names it, which may differ from its action.
    name: str = ""


@dataclass(frozen=True)
class ToolRequested:
    """A tool waits for the Harness to allow or reject it."""

    session: str
    request: str
    action: str
    resources: tuple[str, ...]
    #: The ``ToolCalled`` it asks for; empty when the Engine does not say.
    call: str = ""
    #: Patterns the Engine suggests for allowing it again without asking.
    patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolFinished:
    """A tool has run: what it gave back, or why it failed."""

    session: str
    call: str
    output: str
    error: str = ""
    #: A command's exit status, when the tool ran one.
    exit: int | None = None


@dataclass(frozen=True)
class Delivered:
    """A message that waited while the model worked has reached it."""

    session: str
    message: str


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


Event = (
    Text
    | ToolCalled
    | ToolRequested
    | ToolFinished
    | Delivered
    | Answered
    | Finished
    | Stopped
    | Failed
)


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
    #: The question's message at the Engine.
    message: str = ""


@dataclass(frozen=True)
class FileChange:
    """A file a revert puts back: what happens to it, and the diff."""

    path: str
    status: str
    additions: int
    deletions: int
    patch: str


@dataclass(frozen=True)
class Revert:
    """A revert staged by the Engine: the files it put back, and whether it
    could put files back at all (outside a git repository it cannot)."""

    files: tuple[FileChange, ...]
    restorable: bool


@runtime_checkable
class Engine(Protocol):
    def start(
        self, model: ModelRef | None = None, directory: Path | None = None
    ) -> str:
        """Open a session and return its id; None leaves the Engine's default
        model, or its own folder."""
        ...

    def send(self, session: str, text: str) -> str:
        """Send a message; while the session is busy it waits and steers the
        model at its next step. Answers where it waits."""
        ...

    def withdraw(self, session: str, message: str) -> None:
        """Take back a message that is still waiting."""
        ...

    def events(self) -> Iterator[Event]:
        """Every session's events, for as long as the Engine runs."""
        ...

    def reply(self, session: str, request: str, answer: Reply, message: str) -> None:
        """Answer a ``ToolRequested``; ``message`` is passed to the model."""
        ...

    def revert(self, session: str, message: str) -> Revert:
        """Stage going back to before ``message``, a question of the session's;
        the files are put back at once, the Conversation when it is kept."""
        ...

    def changes(self, session: str, message: str) -> tuple[FileChange, ...]:
        """What the question ``message`` changed, file by file."""
        ...

    def keep_revert(self, session: str) -> None:
        """Keep the staged revert: the later questions leave the Conversation."""
        ...

    def cancel_revert(self, session: str) -> None:
        """Drop the staged revert: the files it put back return."""
        ...

    def stop(self, session: str) -> None: ...

    def cut_in(self, session: str) -> None:
        """Stop the step under way and go on at once with what was sent."""
        ...

    def switch_model(self, session: str, model: ModelRef) -> None: ...

    def rename(self, session: str, title: str) -> None: ...

    def archive(self, session: str) -> None:
        """Keep a session, out of the way: it leaves the history."""
        ...

    def delete(self, session: str) -> None: ...

    def where(self, session: str) -> Path:
        """The folder a session runs in."""
        ...

    def move(self, session: str, directory: Path) -> None:
        """Carry on the session in another folder: its Project."""
        ...

    def conversations(self) -> list[Past]:
        """The Harness's own sessions, newest first; other programs' are left out."""
        ...

    def history(self, session: str) -> list[PastTurn]: ...

    def attach_tools(self, name: str, command: list[str], directory: Path) -> None:
        """Run a tool server for every session; each of its tools still raises
        a ``ToolRequested`` before it runs."""
        ...

    def action(self, server: str, tool: str) -> str:
        """The action a ``ToolRequested`` names for one of a tool server's tools."""
        ...
