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
