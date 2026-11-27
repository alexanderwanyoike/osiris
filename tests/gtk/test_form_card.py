"""The card for what the model asks the person: each question, its choices,
and the person's answer."""

from __future__ import annotations

from form_card import FormCard
from gi.repository import Gtk

from osiris.harness.engine import Choice, FormAnswer, FormAsked, FormField

from .conftest import find, texts, widgets

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


def card(*fields: FormField) -> tuple[FormCard, list[dict[str, FormAnswer]]]:
    answers: list[dict[str, FormAnswer]] = []
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


def choice(widget: FormCard, label: str) -> Gtk.CheckButton:
    """A choice's radio button, or its tick where several may be picked."""
    return next(
        w
        for w in widgets(widget)
        if isinstance(w, Gtk.CheckButton) and label in texts(w)
    )


def send(widget: FormCard) -> None:
    find(widget, Gtk.Button, "Send").emit("clicked")


def test_a_choice_waits_for_send_so_a_slip_can_be_changed() -> None:
    """What the model does next rests on it: a Theme pair made, say."""
    widget, answers = card(MOOD)
    choice(widget, "Soft violet").set_active(True)
    choice(widget, "Deep dusk").set_active(True)
    assert answers == []
    send(widget)
    assert answers == [{"q0": "Deep dusk"}]


def test_one_question_can_be_answered_in_the_persons_own_words() -> None:
    widget, answers = card(MOOD)
    entry = find(widget, Gtk.Entry, "Or type your own answer")
    entry.set_text("Violet with a gold horizon")
    entry.emit("activate")
    assert answers == [{"q0": "Violet with a gold horizon"}]


EXTRAS = FormField(
    "q1",
    "Extras",
    "What else should change?",
    (Choice("Wallpaper", "Wallpaper"), Choice("Icons", "Icons")),
    multiple=True,
)


def test_several_questions_are_answered_together() -> None:
    widget, answers = card(MOOD, EXTRAS)
    choice(widget, "Deep dusk").set_active(True)
    choice(widget, "Wallpaper").set_active(True)
    choice(widget, "Icons").set_active(True)
    assert answers == []
    send(widget)
    assert answers == [{"q0": "Deep dusk", "q1": ("Wallpaper", "Icons")}]


def test_a_question_left_unanswered_is_left_out() -> None:
    """opencode tells the model it went unanswered; an empty answer would
    read as one."""
    widget, answers = card(MOOD, EXTRAS)
    choice(widget, "Wallpaper").set_active(True)
    send(widget)
    assert answers == [{"q1": ("Wallpaper",)}]
