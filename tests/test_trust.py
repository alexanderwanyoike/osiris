"""Whether the person has allowed the Harness everything."""

from __future__ import annotations

from pathlib import Path

from osiris.harness.trust import allow_everything, allows_everything
from osiris.platform import FakeFileSystem

HOME = Path("/home/tester")


def test_nothing_is_allowed_beyond_the_tiers_until_the_person_says_so() -> None:
    assert not allows_everything(FakeFileSystem(), HOME)


def test_allowing_everything_is_kept() -> None:
    files = FakeFileSystem()
    allow_everything(files, HOME, on=True)
    assert allows_everything(files, HOME)


def test_allowing_everything_can_be_turned_off_again() -> None:
    files = FakeFileSystem()
    allow_everything(files, HOME, on=True)
    allow_everything(files, HOME, on=False)
    assert not allows_everything(files, HOME)
