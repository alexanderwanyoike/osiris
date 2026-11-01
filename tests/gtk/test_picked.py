"""What the person picks in the message box reaches the Engine with the text,
however the message is sent."""

from __future__ import annotations

import threading

from osiris.harness.picker import Entry, Reference

from .test_side_by_side import app, asked

REVIEW = Reference(Entry("skill", "review", "review", ""), 0, 7)


def sent_off() -> None:
    """Questions go to the Engine on a thread of their own."""
    for thread in threading.enumerate():
        if thread is not threading.current_thread() and thread.daemon:
            thread.join(timeout=5)


def test_what_was_picked_goes_with_a_question() -> None:
    stand_in, engine = app()
    stand_in.ask("/review the timer", (REVIEW,))
    sent_off()
    assert engine.referenced == [("ses_1", (REVIEW,))]


def test_what_was_picked_goes_with_a_message_sent_while_osiris_works() -> None:
    stand_in, engine = app()
    asked(stand_in, "make it calm")
    stand_in.ask("/review the timer", (REVIEW,))
    assert engine.referenced == [("ses_1", (REVIEW,))]
