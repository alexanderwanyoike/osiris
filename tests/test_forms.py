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
