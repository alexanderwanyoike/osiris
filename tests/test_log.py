"""The Harness log read back: the changes the last question led to, so the
drawer can offer to undo them."""

from __future__ import annotations

from pathlib import Path

from osiris.harness.log import LOG_FILE, Change, HarnessLog
from osiris.platform import FakeFileSystem

HOME = Path("/home/tester")


def log() -> HarnessLog:
    return HarnessLog(FakeFileSystem(), HOME / LOG_FILE)


def test_with_nothing_logged_there_are_no_changes() -> None:
    assert log().last_changes() == []


def test_the_changes_are_those_logged_since_the_last_question() -> None:
    subject = log()
    subject.write("sent", session="ses_1", text="make it calm")
    subject.write("changed", summary="Made Calm", undo=None)
    subject.write("sent", session="ses_1", text="make it warmer")
    subject.write("allowed", session="ses_1", action="osiris_create_theme")
    subject.write(
        "changed",
        summary="Made Ember",
        undo={"action": "delete_theme", "name": "ember"},
    )
    subject.write(
        "changed",
        summary="Applied Ember",
        undo={"action": "apply_theme", "name": "calm"},
    )
    assert subject.last_changes() == [
        Change("Made Ember", {"action": "delete_theme", "name": "ember"}),
        Change("Applied Ember", {"action": "apply_theme", "name": "calm"}),
    ]
