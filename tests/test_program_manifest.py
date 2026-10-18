"""The Program manifest: what a Program is called and how it runs, and the
menu entry made from it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from osiris.programs.manifest import Manifest, ManifestError, desktop_entry, dump, parse

INSTALLED = Path("/home/tester/.local/share/osiris/programs/pomodoro")

POMODORO = {
    "name": "pomodoro",
    "label": "Pomodoro",
    "description": "A focus timer: 25 minutes on, 5 off.",
    "icon": "icon.svg",
    "build": ["cargo", "build", "--release"],
    "run": ["target/release/pomodoro"],
    "terminal": False,
}


def manifest(**changes: object) -> Manifest:
    return parse(json.dumps({**POMODORO, **changes}))


def test_a_manifest_reads_every_field() -> None:
    assert manifest() == Manifest(
        name="pomodoro",
        label="Pomodoro",
        description="A focus timer: 25 minutes on, 5 off.",
        icon="icon.svg",
        build=("cargo", "build", "--release"),
        run=("target/release/pomodoro",),
        terminal=False,
    )


def test_an_icon_a_build_and_the_terminal_are_optional() -> None:
    text = json.dumps(
        {
            "name": "hello",
            "label": "Hello",
            "description": "Says hello.",
            "run": ["python3", "main.py"],
        }
    )
    assert parse(text) == Manifest(
        name="hello",
        label="Hello",
        description="Says hello.",
        icon=None,
        build=None,
        run=("python3", "main.py"),
        terminal=False,
    )


def test_a_manifest_survives_being_written_and_read_again() -> None:
    assert parse(dump(manifest())) == manifest()


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"run": None}, "run"),
        ({"run": "python3 main.py"}, "a list of words, not a shell line"),
        ({"run": []}, "a list of words, not a shell line"),
        ({"name": "Pomodoro Timer"}, "lower case"),
        ({"icon": "/usr/share/icons/x.svg"}, "inside the Program"),
        ({"icon": "../elsewhere.svg"}, "inside the Program"),
        ({"terminal": "yes"}, "true or false"),
        ({"label": "Timer\nExec=rm -rf ~"}, "one line"),
        ({"description": "Ticks\nTerminal=true"}, "one line"),
        ({"run": ["python3", "main.py\nTerminal=true"]}, "one line"),
    ],
)
def test_a_bad_manifest_says_what_to_fix(
    changes: dict[str, object], reason: str
) -> None:
    fields = {k: v for k, v in {**POMODORO, **changes}.items() if v is not None}
    with pytest.raises(ManifestError, match=reason):
        parse(json.dumps(fields))


def test_text_that_is_not_json_is_refused() -> None:
    with pytest.raises(ManifestError, match="JSON"):
        parse("name = pomodoro")


def entry(m: Manifest) -> dict[str, str]:
    lines = desktop_entry(m, INSTALLED).splitlines()
    assert lines[0] == "[Desktop Entry]"
    return dict(line.split("=", 1) for line in lines[1:] if line)


def test_the_menu_entry_names_and_describes_the_program() -> None:
    fields = entry(manifest())
    assert fields["Type"] == "Application"
    assert fields["Name"] == "Pomodoro"
    assert fields["Comment"] == "A focus timer: 25 minutes on, 5 off."
    assert fields["X-Osiris-Program"] == "pomodoro"


def test_the_menu_entry_runs_the_installed_copy_from_its_folder() -> None:
    fields = entry(manifest())
    assert fields["Exec"] == f"{INSTALLED}/target/release/pomodoro"
    assert fields["Path"] == str(INSTALLED)
    assert fields["Icon"] == f"{INSTALLED}/icon.svg"
    assert fields["Terminal"] == "false"


def test_a_command_on_the_path_is_run_by_name() -> None:
    fields = entry(manifest(run=["python3", "main.py"]))
    assert fields["Exec"] == "python3 main.py"


def test_a_program_without_an_icon_gets_a_generic_one() -> None:
    assert entry(manifest(icon=None))["Icon"] == "application-x-executable"


def test_a_script_opens_in_a_terminal() -> None:
    assert entry(manifest(terminal=True))["Terminal"] == "true"


def test_words_with_spaces_or_percent_signs_are_quoted_for_the_menu() -> None:
    fields = entry(manifest(run=["python3", "my timer.py", "--at", "50%"]))
    assert fields["Exec"] == 'python3 "my timer.py" --at 50%%'
