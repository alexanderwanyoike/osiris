"""What a step shows when it is opened: what Thoth asked for, what came back."""

from __future__ import annotations

from osiris.harness.activity import Step
from osiris.harness.detail import Kind, detail


def test_a_command_shows_its_command_line_and_output() -> None:
    step = Step(
        "shell",
        ("ls /etc",),
        input={"command": "ls /etc | head -2"},
        output="NetworkManager\nUPower\n",
        exit=0,
    )
    shown = detail(step)
    assert shown.kind is Kind.COMMAND
    assert shown.asked == "ls /etc | head -2"
    assert [line.text for line in shown.lines] == ["NetworkManager", "UPower"]
    assert shown.note == ""


def test_a_command_that_failed_says_how_it_exited() -> None:
    step = Step("shell", ("false",), input={"command": "false"}, exit=1)
    assert detail(step).note == "Exited with status 1"


def test_a_file_edit_shows_the_change_as_a_diff() -> None:
    step = Step(
        "edit",
        ("Code/pomodoro/main.py",),
        input={
            "path": "/home/tester/Code/pomodoro/main.py",
            "oldString": "minutes = 25\nprint(minutes)",
            "newString": "minutes = 50\nprint(minutes)",
        },
    )
    shown = detail(step)
    assert shown.kind is Kind.CHANGE
    assert shown.asked == "/home/tester/Code/pomodoro/main.py"
    assert [(line.mark, line.text) for line in shown.lines] == [
        ("-", "minutes = 25"),
        ("+", "minutes = 50"),
        (" ", "print(minutes)"),
    ]
