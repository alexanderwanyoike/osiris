"""What a Conversation is called: its first question, shortened to fit."""

from __future__ import annotations

#: How much of the first question a title keeps.
TITLE_LENGTH = 48


def title_of(question: str) -> str:
    line = question.strip().splitlines()[0]
    if len(line) <= TITLE_LENGTH:
        return line
    return line[:TITLE_LENGTH].rsplit(" ", 1)[0] + "…"
