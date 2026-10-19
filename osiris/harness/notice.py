"""What the desktop notification says when an answer ends unread; the
drawer only sends it."""

from __future__ import annotations

from dataclasses import dataclass

from osiris.harness.conversation import Conversation, State


@dataclass(frozen=True)
class Notice:
    title: str
    body: str


def notice_of(conversation: Conversation) -> Notice:
    turn = conversation.turns[-1]
    if turn.state is State.FAILED:
        return Notice("Osiris could not finish", f"{conversation.title}\n{turn.error}")
    return Notice("Osiris replied", f"{conversation.title}\n{turn.answer}")
