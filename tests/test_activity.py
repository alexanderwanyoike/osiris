"""Each step of an answer in plain words, as the drawer shows it."""

from __future__ import annotations

import pytest

from osiris.harness.activity import Step


@pytest.mark.parametrize(
    ("action", "resources", "doing"),
    [
        ("read", ("main.py",), "Reading main.py"),
        ("edit", ("pomodoro/main.py",), "Editing pomodoro/main.py"),
        ("list", ("pomodoro",), "Listing pomodoro"),
    ],
)
def test_a_file_step_says_what_it_is_doing_to_which_file(
    action: str, resources: tuple[str, ...], doing: str
) -> None:
    assert Step(action, resources).doing == doing


@pytest.mark.parametrize(
    ("action", "resources", "record"),
    [
        ("read", ("main.py",), "Read main.py"),
        ("edit", ("pomodoro/main.py",), "Edited pomodoro/main.py"),
        ("list", ("pomodoro",), "Listed pomodoro"),
    ],
)
def test_a_finished_step_is_recorded_in_the_past_tense(
    action: str, resources: tuple[str, ...], record: str
) -> None:
    assert Step(action, resources).record == record


@pytest.mark.parametrize(
    ("path", "shown"),
    [
        ("/home/tester/Code/pomodoro/main.py", "pomodoro/main.py"),
        ("Code/pomodoro/src/timer.py", "src/timer.py"),
        ("/home/tester/Code/pomodoro/*", "Code/pomodoro"),
    ],
)
def test_a_long_path_is_shown_by_its_last_two_parts(path: str, shown: str) -> None:
    assert Step("read", (path,)).doing == f"Reading {shown}"
