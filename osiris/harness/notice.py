"""What the desktop notification says when an answer ends unread; the
drawer only sends it."""

from __future__ import annotations

from dataclasses import dataclass

from osiris.harness.conversation import Conversation, State
from osiris.harness.markdown import first_line

#: How much of an answer or a failure a notice tells.
GLANCE = 72


@dataclass(frozen=True)
class Notice:
    title: str
    body: str


def notice_of(conversation: Conversation) -> Notice:
    turn = conversation.turns[-1]
    if turn.state is State.FAILED:
        return Notice(
            "Osiris could not finish", f"{conversation.title}\n{_start(turn.error)}"
        )
    return Notice("Osiris replied", f"{conversation.title}\n{_start(turn.answer)}")


def _start(text: str) -> str:
    line = first_line(text)
    if len(line) <= GLANCE:
        return line
    return line[:GLANCE].rsplit(" ", 1)[0] + "…"
