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
