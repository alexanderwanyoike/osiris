"""What the desktop notification says when an answer ends unread."""

from __future__ import annotations

from osiris.harness.conversation import Conversation
from osiris.harness.engine import Event, Finished, Text
from osiris.harness.notice import Notice, notice_of


def answered(question: str, *events: Event) -> Conversation:
    talk = Conversation()
    talk.asked(question)
    for event in events:
        talk.apply(event)
    return talk


def test_a_finished_answer_says_osiris_replied_with_the_title_and_the_answer() -> None:
    talk = answered(
        "Make me a calm theme",
        Text("ses_1", "I made Calm and applied it."),
        Finished("ses_1"),
    )
    assert notice_of(talk) == Notice(
        "Osiris replied", "Make me a calm theme\nI made Calm and applied it."
    )
