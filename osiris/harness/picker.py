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
