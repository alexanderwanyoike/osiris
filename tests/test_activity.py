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


def test_a_step_on_several_files_names_the_first_and_counts_the_rest() -> None:
    step = Step("edit", ("pomodoro/main.py", "pomodoro/timer.py", "README.md"))
    assert step.doing == "Editing pomodoro/main.py and 2 more"


@pytest.mark.parametrize(
    ("tool", "doing", "record"),
    [
        ("list_themes", "Looking at the themes", "Looked at the themes"),
        ("create_theme", "Making a theme", "Made a theme"),
        ("apply_theme", "Applying a theme", "Applied a theme"),
        ("list_programs", "Looking at your programs", "Looked at your programs"),
        ("create_program", "Starting a program", "Started a program"),
        ("commit_program", "Saving a change", "Saved a change"),
        ("check_program", "Checking the program", "Checked the program"),
    ],
)
def test_an_osiris_tool_is_named_by_what_it_does(
    tool: str, doing: str, record: str
) -> None:
    step = Step(f"osiris_{tool}", ("*",))
    assert (step.doing, step.record) == (doing, record)


@pytest.mark.parametrize("action", ["bash", "shell"])
def test_a_command_is_named_as_written(action: str) -> None:
    step = Step(action, ("ls /etc",))
    assert (step.doing, step.record) == ("Running ls /etc", "Ran ls /etc")
