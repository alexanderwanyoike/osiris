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


def test_a_read_shows_what_was_looked_at_and_what_was_found() -> None:
    step = Step(
        "read",
        ("/etc/hostname",),
        input={"path": "/etc/hostname"},
        output="1: osiris",
    )
    shown = detail(step)
    assert (shown.kind, shown.asked) == (Kind.LOOK, "/etc/hostname")
    assert [line.text for line in shown.lines] == ["1: osiris"]


def test_a_search_shows_its_pattern() -> None:
    step = Step("grep", ("TODO",), input={"pattern": "TODO", "path": "src"})
    assert detail(step).asked == "TODO in src"


def test_a_web_search_shows_its_query_and_what_came_back() -> None:
    step = Step(
        "websearch",
        ("gtk4 popover",),
        input={"query": "gtk4 popover"},
        output="GtkPopover - docs.gtk.org",
    )
    shown = detail(step)
    assert (shown.kind, shown.asked) == (Kind.WEB, "gtk4 popover")


def test_a_page_fetch_shows_its_address() -> None:
    step = Step("webfetch", ("docs.gtk.org",), input={"url": "https://docs.gtk.org"})
    assert detail(step).asked == "https://docs.gtk.org"


def test_an_osiris_tool_shows_its_name_inputs_and_result_in_words() -> None:
    step = Step(
        "osiris_apply_theme",
        ("*",),
        input={"name": "calm-night", "dark": True},
        output="Applied Calm Night.",
    )
    shown = detail(step)
    assert (shown.kind, shown.asked) == (Kind.TOOL, "apply theme")
    assert shown.inputs == (("name", "calm-night"), ("dark", "yes"))
    assert [line.text for line in shown.lines] == ["Applied Calm Night."]
