"""A Conversation that starts waiting for the person says so in the sidebar,
and on the desktop when the person is not looking (#152)."""

from __future__ import annotations

from osiris.harness.engine import ToolRequested
from osiris.harness.status import Status

from .test_side_by_side import app, asked, heard


def test_a_conversation_waiting_for_the_person_says_so() -> None:
    stand_in, _ = app()
    asked(stand_in, "list /etc")
    heard(stand_in, ToolRequested("ses_1", "per_1", "shell", ("ls /etc",)))
    assert stand_in.statuses == {"ses_1": Status.WAITING}


def test_a_conversation_starting_to_wait_unseen_is_told_on_the_desktop() -> None:
    stand_in, _ = app()
    asked(stand_in, "list /etc")
    stand_in.open = False
    heard(stand_in, ToolRequested("ses_1", "per_1", "shell", ("ls /etc",)))
    assert [session for session, _ in stand_in.sent] == ["ses_1"]


def test_a_conversation_starting_to_wait_in_view_is_not_told() -> None:
    stand_in, _ = app()
    asked(stand_in, "list /etc")
    heard(stand_in, ToolRequested("ses_1", "per_1", "shell", ("ls /etc",)))
    assert stand_in.sent == []


def test_answering_a_card_tells_the_sidebar_the_conversation_stopped_waiting() -> None:
    from osiris.harness.harness import Answer

    stand_in, _ = app()
    asked(stand_in, "list /etc")
    heard(stand_in, ToolRequested("ses_1", "per_1", "shell", ("ls /etc",)))
    seen = stand_in.histories
    asking = stand_in.conversation.turns[-1].asking
    assert asking is not None
    stand_in.answer_card(asking, Answer.ONCE, "")
    assert stand_in.statuses == {"ses_1": Status.WORKING}
    assert stand_in.histories > seen
