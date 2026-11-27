"""What the model asks waits on a card in the sidebar, and the person's
answer reaches the Engine (the question tool hung without one)."""

from __future__ import annotations

from osiris.harness.engine import Choice, FormAsked, FormField
from osiris.harness.status import Status

from .test_form_card import choice
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


def test_answering_the_card_reaches_the_engine_and_the_card_goes() -> None:
    stand_in, engine = app()
    asked(stand_in, "make it lavender at dusk")
    heard(stand_in, MOOD)
    turn = stand_in.conversation.turns[-1]
    choice(stand_in.form_card(turn), "Deep dusk").emit("clicked")
    assert engine.forms_answered == [("ses_1", "frm_1", {"q0": "Deep dusk"})]
    assert turn.form is None
    assert stand_in.statuses == {"ses_1": Status.WORKING}


def test_the_card_is_the_same_one_each_time_it_is_drawn() -> None:
    """What is typed in it survives a redraw."""
    stand_in, _ = app()
    asked(stand_in, "make it lavender at dusk")
    heard(stand_in, MOOD)
    turn = stand_in.conversation.turns[-1]
    assert stand_in.form_card(turn) is stand_in.form_card(turn)
