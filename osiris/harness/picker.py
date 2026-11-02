"""The composer's picker (#153): / lists skills and commands, @ lists the
Project's files. It opens on a sign at the start of the word being typed."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

SIGNS = ("@", "/")
SIGN = {
    "file": "@",
    "resource": "@",
    "connector": "@",
    "skill": "/",
    "command": "/",
}


@dataclass(frozen=True)
class Trigger:
    sign: str
    #: Where the sign is in the text.
    start: int
    #: What follows it, which filters the picker.
    query: str


def trigger(text: str, cursor: int) -> Trigger | None:
    """The picker the word ending at ``cursor`` opens, if it starts with a sign."""
    start = cursor
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    word = text[start:cursor]
    if not word or word[0] not in SIGNS:
        return None
    return Trigger(word[0], start, word[1:])


@dataclass(frozen=True)
class Entry:
    #: "file", "resource", "connector", "skill" or "command".
    kind: str
    #: What it names to the Engine: a path in the Project, a skill's id, a name.
    key: str
    label: str
    description: str


def matching(entries: list[Entry], query: str) -> list[Entry]:
    """Those whose label starts with ``query``, then those containing it."""
    wanted = query.lower()
    starts = [e for e in entries if e.label.lower().startswith(wanted)]
    contains = [e for e in entries if wanted in e.label.lower() and e not in starts]
    return starts + contains


def project_files(source: Path, files: list[Path]) -> list[Entry]:
    """``files``, relative to the Program at ``source``, as @ offers them."""
    return [Entry("file", str(source / path), str(path), "") for path in files]


@dataclass(frozen=True)
class Reference:
    """An entry picked into a message, mentioned at ``start`` to ``end``."""

    entry: Entry
    start: int
    end: int


class Skills(Protocol):
    def skills(self, directory: Path) -> list[Entry]:
        """The skills a session in the folder can load."""
        ...


def references(text: str, picked: list[Entry]) -> tuple[Reference, ...]:
    """Where each picked entry is first mentioned as a token in ``text``.

    Found at send time rather than kept from the moment of picking, so edits
    made after picking cannot leave a reference pointing at the wrong text;
    a token deleted since is not sent at all."""
    found = []
    for entry in picked:
        token = SIGN[entry.kind] + entry.label
        match = re.search(rf"(?<!\S){re.escape(token)}(?![\w/])", text)
        if match:
            found.append(Reference(entry, match.start(), match.end()))
    return tuple(sorted(found, key=lambda reference: reference.start))
