"""Each Conversation's status at a glance in the sidebar."""

from __future__ import annotations

from osiris.harness.status import Status, status_of

NONE: frozenset[str] = frozenset()


def test_a_conversation_answering_is_working() -> None:
    assert status_of("a", running={"a"}, waiting=NONE, unread=NONE) is Status.WORKING


def test_a_conversation_with_a_card_open_is_waiting_for_the_person() -> None:
    status = status_of("a", running={"a"}, waiting={"a"}, unread=NONE)
    assert status is Status.WAITING


def test_an_answer_ended_and_unread_is_done() -> None:
    assert status_of("a", running=NONE, waiting=NONE, unread={"a"}) is Status.DONE


def test_a_conversation_read_and_idle_shows_nothing() -> None:
    assert status_of("a", running=NONE, waiting=NONE, unread=NONE) is None


def test_each_status_reads_in_plain_words() -> None:
    assert [s.value for s in Status] == ["Working", "Waiting for you", "Done"]
