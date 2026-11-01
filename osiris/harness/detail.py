"""What a step shows when it is opened: what Thoth asked for, and what came
back, drawn for the kind of step it is. GTK draws it; this decides it."""

from __future__ import annotations

import difflib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from enum import Enum

from osiris.harness.activity import Step


class Kind(Enum):
    COMMAND = "command"
    CHANGE = "change"
    LOOK = "look"
    WEB = "web"
    TOOL = "tool"


@dataclass(frozen=True)
class Line:
    text: str
    #: ``+`` added, ``-`` removed, `` `` unchanged; output is unchanged.
    mark: str = " "


@dataclass(frozen=True)
class Detail:
    kind: Kind
    #: The command line, the path, the query or the tool's inputs.
    asked: str
    #: What came back, or the change made.
    lines: tuple[Line, ...]
    #: An exit status, an error, or the rule that refused the step.
    note: str = ""
    #: A tool's inputs, each as a name and a value in words.
    inputs: tuple[tuple[str, str], ...] = ()


def _text(inputs: Mapping[str, object], *keys: str) -> str:
    """The first of ``keys`` the input has as text; tools name them variously."""
    for key in keys:
        value = inputs.get(key)
        if isinstance(value, str):
            return value
    return ""


def _output(step: Step) -> tuple[Line, ...]:
    return tuple(Line(text) for text in step.output.splitlines())


def _command(step: Step) -> Detail:
    asked = _text(step.input or {}, "command") or " ".join(step.resources)
    failed = step.exit is not None and step.exit != 0
    note = f"Exited with status {step.exit}" if failed else ""
    return Detail(Kind.COMMAND, asked, _output(step), note)


def _change(step: Step) -> Detail:
    """The change as the model asked for it: what was there, what replaced it."""
    inputs = step.input or {}
    old = _text(inputs, "oldString", "old_string").splitlines()
    new = _text(inputs, "newString", "new_string", "content").splitlines()
    rows = difflib.unified_diff(old, new, lineterm="")
    lines = tuple(
        Line(row[1:], row[0])
        for row in rows
        if not row.startswith(("---", "+++", "@@"))
    )
    path = _text(inputs, "path", "filePath", "file_path")
    return Detail(Kind.CHANGE, path or " ".join(step.resources), lines)


def _look(step: Step) -> Detail:
    """A read, listing or search: the path or pattern, and where it looked."""
    inputs = step.input or {}
    pattern = _text(inputs, "pattern", "query")
    path = _text(inputs, "path", "filePath", "file_path")
    asked = f"{pattern} in {path}" if pattern and path else pattern or path
    return Detail(Kind.LOOK, asked or " ".join(step.resources), _output(step))


def _web(step: Step) -> Detail:
    asked = _text(step.input or {}, "query", "url")
    return Detail(Kind.WEB, asked or " ".join(step.resources), _output(step))


def _words(value: object) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return value if isinstance(value, str) else json.dumps(value)


def _tool(step: Step) -> Detail:
    """Any other tool, the Osiris tools among them: its name and inputs."""
    name = step.action.removeprefix("osiris_").replace("_", " ")
    inputs = tuple((key, _words(value)) for key, value in (step.input or {}).items())
    return Detail(Kind.TOOL, name, _output(step), inputs=inputs)


_KINDS: dict[str, Callable[[Step], Detail]] = {
    "shell": _command,
    "bash": _command,
    "edit": _change,
    "write": _change,
    "read": _look,
    "list": _look,
    "glob": _look,
    "grep": _look,
    "external_directory": _look,
    "websearch": _web,
    "web_search": _web,
    "webfetch": _web,
}


def detail(step: Step) -> Detail:
    shown = _KINDS.get(step.action, _tool)(step)
    return replace(shown, note=step.refused_by or step.error or shown.note)


#: How many lines of what came back show before the rest is folded away.
FOLD = 12


def folded(lines: tuple[Line, ...]) -> tuple[tuple[Line, ...], int]:
    """The lines to show at first, and how many are folded away after them."""
    if len(lines) <= FOLD:
        return lines, 0
    return lines[:FOLD], len(lines) - FOLD
