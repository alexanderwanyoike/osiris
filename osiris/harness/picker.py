"""The composer's picker (#153): / lists skills and commands, @ lists the
Project's files. It opens on a sign at the start of the word being typed."""

from __future__ import annotations

from dataclasses import dataclass

SIGNS = ("@", "/")


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
    #: "file", "skill" or "command".
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


@dataclass(frozen=True)
class Reference:
    """An entry picked into a message, mentioned at ``start`` to ``end``."""

    entry: Entry
    start: int
    end: int
