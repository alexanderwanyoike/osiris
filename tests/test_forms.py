"""The reply to a form, from what the person picked and typed."""

from __future__ import annotations

from osiris.harness.engine import Choice, FormAsked, FormField
from osiris.harness.forms import reply

EXTRAS = FormAsked(
    "ses_1",
    "frm_1",
    (
        FormField(
            "q1",
            "Extras",
            "What else should change?",
            (Choice("Wallpaper", "Wallpaper"), Choice("Icons", "Icons")),
            multiple=True,
            custom=True,
        ),
    ),
)


def test_a_typed_answer_where_several_may_be_picked_joins_those_ticked() -> None:
    """opencode takes only a list there; a lone string fails the whole reply."""
    assert reply(EXTRAS, {"q1": ("Wallpaper",)}, {"q1": " Clock "}) == {
        "q1": ("Wallpaper", "Clock")
    }


MOOD = FormAsked(
    "ses_1",
    "frm_1",
    (
        FormField(
            "q0",
            "Mood",
            "Which dusk?",
            (Choice("Deep dusk", "Deep dusk"),),
            custom=True,
        ),
    ),
)


def test_a_typed_answer_wins_over_a_choice_where_one_may_be_picked() -> None:
    assert reply(MOOD, {"q0": ("Deep dusk",)}, {"q0": "Violet"}) == {"q0": "Violet"}


def test_a_question_left_unanswered_is_left_out() -> None:
    """opencode tells the model it went unanswered; an empty one reads as said."""
    assert reply(MOOD, {"q0": ()}, {"q0": "  "}) == {}
