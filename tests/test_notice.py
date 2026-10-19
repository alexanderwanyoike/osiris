"""What the desktop notification says when an answer ends unread."""

from __future__ import annotations

from osiris.harness.conversation import Conversation
from osiris.harness.engine import Event, Failed, Finished, Text
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


def test_a_failed_answer_says_osiris_could_not_finish_and_why() -> None:
    talk = answered(
        "Make me a calm theme",
        Text("ses_1", "Starting on"),
        Failed("ses_1", "The provider's limit was reached"),
    )
    assert notice_of(talk) == Notice(
        "Osiris could not finish",
        "Make me a calm theme\nThe provider's limit was reached",
    )


def test_only_the_start_of_the_answer_is_told_on_one_line() -> None:
    """A notification is a glance; the drawer holds the rest."""
    talk = answered(
        "Build me a timer",
        Text(
            "ses_1",
            "\nI built Pomodoro, a timer that counts down twenty-five minutes "
            "of work and then five of rest, and rings between them.\n\n"
            "Try it from the card below.",
        ),
        Finished("ses_1"),
    )
    _, line = notice_of(talk).body.split("\n")
    assert (
        line
        == "I built Pomodoro, a timer that counts down twenty-five minutes of work…"
    )
