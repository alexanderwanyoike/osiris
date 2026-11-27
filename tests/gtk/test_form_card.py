"""The card for what the model asks the person: each question, its choices,
and the person's answer."""

from __future__ import annotations

from form_card import FormCard

from osiris.harness.engine import Choice, FormAsked, FormField

from .conftest import texts

MOOD = FormField(
    "q0",
    "Mood",
    "Which dusk should it be?",
    (
        Choice("Soft violet", "Soft violet", "Pale lilac and grey"),
        Choice("Deep dusk", "Deep dusk", "Indigo and amber"),
    ),
    custom=True,
)


def card(*fields: FormField) -> tuple[FormCard, list[dict[str, str | tuple[str, ...]]]]:
    answers: list[dict[str, str | tuple[str, ...]]] = []
    return FormCard(FormAsked("ses_1", "frm_1", fields), on_answer=answers.append), (
        answers
    )


def test_the_card_shows_each_question_and_its_choices() -> None:
    widget, _ = card(MOOD)
    shown = texts(widget)
    for text in (
        "Mood",
        "Which dusk should it be?",
        "Soft violet",
        "Pale lilac and grey",
        "Deep dusk",
        "Indigo and amber",
    ):
        assert text in shown
