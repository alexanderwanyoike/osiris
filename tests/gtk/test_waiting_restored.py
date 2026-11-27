"""A request still waiting when the drawer restarts gets its card back (#182)."""

from __future__ import annotations

from types import SimpleNamespace

from osiris.harness.engine import Choice, FormAsked, FormField, PastTurn, ToolRequested
from tests.test_harness import GPT

from .test_form_card import choice, send
from .test_side_by_side import app, asked


def test_a_request_still_waiting_comes_back_as_its_card() -> None:
    stand_in, _engine = app()
    conversation = asked(stand_in, "list /etc")
    session = stand_in.harness.session or ""
    stand_in.requests = SimpleNamespace(
        waiting=lambda s: [ToolRequested(s, "per_1", "bash", ("ls /etc",))]
    )
    stand_in.restore_waiting(session)
    turn = conversation.turns[-1]
    assert turn.held is not None or turn.asking is not None


def test_a_form_still_open_comes_back_as_its_card_and_answers_the_engine() -> None:
    """The question tool's form outlives a restart of the drawer; without its
    card the answer hangs until stopped."""
    stand_in, engine = app()
    engine.past = [PastTurn("make it lavender at dusk", "", GPT)]
    mood = FormAsked(
        "ses_9",
        "frm_1",
        (FormField("q0", "Mood", "Which dusk?", (Choice("Deep dusk", "Deep dusk"),)),),
    )
    stand_in.requests = SimpleNamespace(waiting=lambda _session: [mood])
    stand_in.open_past("ses_9")
    turn = stand_in.conversation.turns[-1]
    assert turn.form == mood
    card = stand_in.form_card(turn)
    choice(card, "Deep dusk").set_active(True)
    send(card)
    assert engine.forms_answered == [("ses_9", "frm_1", {"q0": "Deep dusk"})]
