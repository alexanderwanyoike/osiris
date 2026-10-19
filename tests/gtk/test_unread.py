"""Conversations as chats: an answer the person has not seen is unread, and
the desktop tells them Osiris got back to them."""

from __future__ import annotations

from osiris.harness.engine import Finished, Text

from .test_side_by_side import app, asked, heard


def test_an_answer_ending_off_screen_leaves_its_conversation_unread() -> None:
    stand_in, _ = app()
    asked(stand_in, "make it calm")
    stand_in.new_conversation()
    heard(stand_in, Text("ses_1", "Calmer now."))
    heard(stand_in, Finished("ses_1"))
    assert stand_in.unread.sessions() == frozenset({"ses_1"})
