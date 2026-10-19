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


def test_a_change_to_a_program_names_it() -> None:
    subject = log()
    subject.write("sent", session="ses_1", text="add a pause button")
    subject.write(
        "changed",
        summary="Pomodoro: Add a pause button",
        undo={"action": "revert_commit", "name": "pomodoro", "commit": "abc"},
        program="pomodoro",
    )
    (change,) = subject.last_changes()
    assert change.program == "pomodoro"


def test_a_change_to_anything_else_names_no_program() -> None:
    subject = log()
    subject.write("changed", summary="Made Harbour", undo=None)
    (change,) = subject.last_changes()
    assert change.program is None


def test_the_log_says_which_program_each_session_worked_on_first() -> None:
    subject = log()
    subject.write("sent", session="ses_1", text="build a timer")
    subject.write("allowed", session="ses_1", action="osiris_create_program")
    subject.write(
        "changed",
        summary="Made Pomodoro",
        undo={"action": "trash_program", "name": "pomodoro"},
        program="pomodoro",
    )
    subject.write(
        "changed",
        summary="Pomodoro: Add a pause",
        undo={"action": "revert_commit", "name": "pomodoro", "commit": "a"},
        program="pomodoro",
    )
    subject.write("sent", session="ses_2", text="make a theme")
    subject.write("changed", summary="Made Harbour", undo=None)
    subject.write("sent", session="ses_3", text="give pomodoro an icon")
    subject.write(
        "changed",
        summary="Pomodoro: Add an icon",
        undo={"action": "revert_commit", "name": "pomodoro", "commit": "b"},
        program="pomodoro",
    )
    assert subject.programs_worked_on() == [
        ("ses_1", "pomodoro"),
        ("ses_3", "pomodoro"),
    ]


def test_the_log_says_which_programs_a_session_changed() -> None:
    subject = log()
    subject.write("sent", session="ses_1", text="build a timer")
    subject.write("changed", summary="Made Pomodoro", undo=None, program="pomodoro")
    subject.write("sent", session="ses_2", text="build notes")
    subject.write("changed", summary="Made Notes", undo=None, program="notes")
    subject.write("sent", session="ses_1", text="add a pause")
    subject.write("changed", summary="Pomodoro: pause", undo=None, program="pomodoro")
    subject.write("changed", summary="Made Clock", undo=None, program="clock")
    assert subject.programs_of("ses_1") == ["pomodoro", "clock"]


def test_forgetting_a_session_erases_everything_logged_for_it() -> None:
    subject = log()
    subject.write("sent", session="ses_1", text="build a timer")
    subject.write("changed", summary="Made Pomodoro", undo=None, program="pomodoro")
    subject.write("sent", session="ses_2", text="hello")
    subject.forget("ses_1")
    assert subject.programs_of("ses_1") == []
    assert subject.last_changes() == []
    subject.write("changed", summary="Made Notes", undo=None, program="notes")
    assert subject.programs_of("ses_2") == ["notes"]


def test_the_tokens_a_session_spent_are_added_up_from_its_answers() -> None:
    subject = log()
    tokens = {
        "input": 100,
        "output": 20,
        "reasoning": 5,
        "cache_read": 900,
        "cache_write": 0,
    }
    subject.write(
        "answered",
        session="ses_1",
        provider="openai",
        model="gpt",
        tokens=tokens,
        cost=0,
    )
    subject.write(
        "answered",
        session="ses_2",
        provider="openai",
        model="gpt",
        tokens=tokens,
        cost=0,
    )
    subject.write(
        "answered",
        session="ses_1",
        provider="openai",
        model="gpt",
        tokens=tokens,
        cost=0,
    )
    assert subject.tokens_spent("ses_1") == 250
    assert subject.tokens_spent("ses_3") == 0


def test_each_question_of_a_session_gets_back_the_changes_it_led_to() -> None:
    subject = log()
    made = {"action": "trash_program", "name": "pomodoro"}
    commit = {"action": "revert_commit", "name": "pomodoro", "commit": "a"}
    subject.write("sent", session="ses_1", text="build a timer")
    subject.write("changed", summary="Made Pomodoro", undo=made, program="pomodoro")
    subject.write("sent", session="ses_2", text="make a theme")
    subject.write("changed", summary="Made Harbour", undo=None)
    subject.write("sent", session="ses_1", text="thanks")
    subject.write("sent", session="ses_1", text="add a pause")
    subject.write("changed", summary="Pomodoro: pause", undo=commit, program="pomodoro")
    assert subject.changes_by_question("ses_1") == [
        [Change("Made Pomodoro", made, program="pomodoro")],
        [],
        [Change("Pomodoro: pause", commit, program="pomodoro")],
    ]
