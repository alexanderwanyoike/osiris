"""What Thoth asks before going back to before a question (#158)."""

from __future__ import annotations

from gi.repository import Adw
from going_back import going_back_dialog

LOST = "This question and its answer leave the Conversation."


def test_it_says_what_will_be_lost_before_editing() -> None:
    dialog = going_back_dialog(LOST, again=False)
    assert dialog.get_heading() == "Edit this question?"
    assert dialog.get_body() == LOST
    assert dialog.get_response_label("back") == "Go back and edit"
    assert dialog.get_close_response() == "cancel"
    assert dialog.get_response_appearance("back") == Adw.ResponseAppearance.DESTRUCTIVE


def test_trying_again_says_so() -> None:
    dialog = going_back_dialog(LOST, again=True)
    assert dialog.get_heading() == "Try this question again?"
    assert dialog.get_response_label("back") == "Go back and try again"
