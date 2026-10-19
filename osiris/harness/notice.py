"""What the desktop notification says when an answer ends unread; the
drawer only sends it."""

from __future__ import annotations

from dataclasses import dataclass

from osiris.harness.conversation import Conversation


@dataclass(frozen=True)
class Notice:
    title: str
    body: str


def notice_of(conversation: Conversation) -> Notice:
    turn = conversation.turns[-1]
    return Notice("Osiris replied", f"{conversation.title}\n{turn.answer}")
