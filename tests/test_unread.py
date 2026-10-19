"""Which Conversations have an answer the person has not seen yet."""

from __future__ import annotations

from pathlib import Path

from osiris.harness.engine import Failed, Finished, Stopped
from osiris.harness.unread import Unread
from osiris.platform import FakeFileSystem

HOME = Path("/home/tester")


def test_an_answer_ending_while_the_person_is_not_looking_leaves_it_unread() -> None:
    unread = Unread(FakeFileSystem(), HOME)
    assert unread.ended(Finished("ses_1"), looking=False)
    assert unread.sessions() == frozenset({"ses_1"})


def test_an_answer_the_person_watched_end_is_read() -> None:
    unread = Unread(FakeFileSystem(), HOME)
    assert not unread.ended(Finished("ses_1"), looking=True)
    assert unread.sessions() == frozenset()


def test_an_answer_the_person_stopped_is_not_unread() -> None:
    """They stopped it themselves, so there is nothing new to tell them."""
    unread = Unread(FakeFileSystem(), HOME)
    assert not unread.ended(Stopped("ses_1"), looking=False)
    assert unread.sessions() == frozenset()


def test_an_answer_that_failed_while_the_person_was_away_is_unread() -> None:
    """They need to know it did not finish as much as that it did."""
    unread = Unread(FakeFileSystem(), HOME)
    assert unread.ended(Failed("ses_1", "the provider refused"), looking=False)
    assert unread.sessions() == frozenset({"ses_1"})
