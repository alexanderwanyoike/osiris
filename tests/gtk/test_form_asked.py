"""What the model asks waits on a card in the sidebar, and the person's
answer reaches the Engine (the question tool hung without one)."""

from __future__ import annotations

from osiris.harness.engine import Choice, FormAsked, FormField

from .test_side_by_side import app, asked, heard

MOOD = FormAsked(
    "ses_1",
    "frm_1",
    (FormField("q0", "Mood", "Which dusk?", (Choice("Deep dusk", "Deep dusk"),)),),
)


def test_a_form_asked_unseen_is_told_on_the_desktop() -> None:
    stand_in, _ = app()
    asked(stand_in, "make it lavender at dusk")
    stand_in.open = False
    heard(stand_in, MOOD)
    assert [session for session, _ in stand_in.sent] == ["ses_1"]
