"""The card under an answer that built a Program: Try, Install or Update."""

from __future__ import annotations

from pathlib import Path

from gi.repository import Gtk
from program_card import ProgramCard

from osiris.programs.manifest import parse
from osiris.programs.programs import Program

from .conftest import find, texts, widgets

MANIFEST = parse(
    '{"name": "pomodoro", "label": "Pomodoro", "description": "A focus timer.",'
    ' "run": ["python3", "main.py"]}'
)


def program(installed: str | None = None, head: str = "abc") -> Program:
    return Program(MANIFEST, Path("/home/tester/Code/pomodoro"), head, installed)


class Clicks:
    def __init__(self) -> None:
        self.tried: list[str] = []
        self.installed: list[str] = []
        self.fixed: list[tuple[str, str]] = []


def card(subject: Program, **state: str) -> tuple[ProgramCard, Clicks]:
    clicks = Clicks()
    widget = ProgramCard(
        subject,
        on_try=clicks.tried.append,
        on_install=clicks.installed.append,
        on_fix=lambda name, problem: clicks.fixed.append((name, problem)),
        **state,
    )
    return widget, clicks


def buttons(root: Gtk.Widget) -> list[str]:
    return [w.get_label() for w in widgets(root) if isinstance(w, Gtk.Button)]


def test_a_new_program_offers_to_be_tried_and_installed() -> None:
    widget, clicks = card(program())
    assert "Pomodoro" in texts(widget)
    assert "A focus timer." in texts(widget)
    find(widget, Gtk.Button, "Try").emit("clicked")
    find(widget, Gtk.Button, "Install").emit("clicked")
    assert clicks.tried == ["pomodoro"]
    assert clicks.installed == ["pomodoro"]


def test_a_program_whose_source_moved_on_offers_an_update() -> None:
    widget, clicks = card(program(installed="old", head="new"))
    find(widget, Gtk.Button, "Update").emit("clicked")
    assert clicks.installed == ["pomodoro"]


def test_an_up_to_date_program_says_it_is_installed() -> None:
    widget, _ = card(program(installed="abc", head="abc"))
    assert "Installed" in texts(widget)
    assert buttons(widget) == ["Try"]


def test_while_building_the_buttons_wait() -> None:
    widget, _ = card(program(), busy="Building…")
    assert "Building…" in texts(widget)
    assert not find(widget, Gtk.Button, "Try").get_sensitive()
    assert not find(widget, Gtk.Button, "Install").get_sensitive()


def test_a_failed_build_is_shown_and_can_go_back_to_the_harness() -> None:
    widget, clicks = card(program(), problem="error: cannot find x")
    assert "error: cannot find x" in texts(widget)
    find(widget, Gtk.Button, "Fix it").emit("clicked")
    assert clicks.fixed == [("pomodoro", "error: cannot find x")]


def test_the_card_shows_the_programs_icon(tmp_path: Path) -> None:
    (tmp_path / "icon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8">'
        '<rect width="8" height="8"/></svg>'
    )
    with_icon = Program(
        parse(
            '{"name": "pomodoro", "label": "Pomodoro", "description": "A timer.",'
            ' "icon": "icon.svg", "run": ["python3", "main.py"]}'
        ),
        tmp_path,
        "abc",
        None,
    )
    widget, _ = card(with_icon)
    files = [
        w.get_property("file") for w in widgets(widget) if isinstance(w, Gtk.Image)
    ]
    assert str(tmp_path / "icon.svg") in files


def test_a_program_without_an_icon_shows_a_generic_one() -> None:
    widget, _ = card(program())
    names = [w.get_icon_name() for w in widgets(widget) if isinstance(w, Gtk.Image)]
    assert "application-x-executable" in names
