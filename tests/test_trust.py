"""Whether the person has turned on auto mode."""

from __future__ import annotations

from pathlib import Path

from osiris.harness.trust import auto_mode_on, turn_auto_mode
from osiris.platform import FakeFileSystem

HOME = Path("/home/tester")


def test_auto_mode_is_off_until_the_person_turns_it_on() -> None:
    assert not auto_mode_on(FakeFileSystem(), HOME)


def test_allowing_everything_is_kept() -> None:
    files = FakeFileSystem()
    turn_auto_mode(files, HOME, on=True)
    assert auto_mode_on(files, HOME)


def test_allowing_everything_can_be_turned_off_again() -> None:
    files = FakeFileSystem()
    turn_auto_mode(files, HOME, on=True)
    turn_auto_mode(files, HOME, on=False)
    assert not auto_mode_on(files, HOME)
