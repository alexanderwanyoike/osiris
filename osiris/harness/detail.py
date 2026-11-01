"""What a step shows when it is opened: what Thoth asked for, and what came
back, drawn for the kind of step it is. GTK draws it; this decides it."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from osiris.harness.activity import Step


class Kind(Enum):
    COMMAND = "command"


@dataclass(frozen=True)
class Line:
    text: str


@dataclass(frozen=True)
class Detail:
    kind: Kind
    #: The command line, the path, the query or the tool's inputs.
    asked: str
    #: What came back.
    lines: tuple[Line, ...]
    #: An exit status, an error, or the rule that refused the step.
    note: str = ""


def detail(step: Step) -> Detail:
    command = (step.input or {}).get("command")
    asked = command if isinstance(command, str) else " ".join(step.resources)
    lines = tuple(Line(text) for text in step.output.splitlines())
    return Detail(Kind.COMMAND, asked, lines)
