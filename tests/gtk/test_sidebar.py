"""The sidebar of Expanded: past Conversations grouped by Project."""

from __future__ import annotations

from pathlib import Path

from gi.repository import Gtk
from sidebar import Sidebar

from osiris.harness.engine import Past
from osiris.harness.history import Project

from .conftest import texts, widgets

HOME = Path("/home/tester")
TIMER = Past("ses_timer", "Build a pomodoro timer", HOME / "Code" / "pomodoro", 30)
THEME = Past("ses_theme", "Make me a calm theme", HOME, 20)
PROJECT = Project("pomodoro", HOME / "Code" / "pomodoro", [TIMER])


class Opened:
    def __init__(self) -> None:
        self.sessions: list[str] = []
        self.new = 0


def sidebar(current: str | None = None) -> tuple[Sidebar, Opened]:
    opened = Opened()
    widget = Sidebar(on_open=opened.sessions.append, on_new=lambda: _new(opened))
    widget.show_history([PROJECT], [THEME], current)
    return widget, opened


def _new(opened: Opened) -> None:
    opened.new += 1


def rows(widget: Sidebar) -> list[Gtk.ListBoxRow]:
    return [w for w in widgets(widget) if isinstance(w, Gtk.ListBoxRow)]


def row_with(widget: Sidebar, text: str) -> Gtk.ListBoxRow:
    return next(row for row in rows(widget) if text in texts(row))


def test_projects_come_first_with_their_conversations_then_the_rest() -> None:
    widget, _ = sidebar()
    shown = texts(widget)
    order = [
        shown.index(t)
        for t in (
            "New conversation",
            "Projects",
            "pomodoro",
            "Build a pomodoro timer",
            "Conversations",
            "Make me a calm theme",
        )
    ]
    assert order == sorted(order)


def test_choosing_a_conversation_opens_it() -> None:
    widget, opened = sidebar()
    widget.list.emit("row-activated", row_with(widget, "Make me a calm theme"))
    assert opened.sessions == ["ses_theme"]


def test_new_conversation_starts_one() -> None:
    widget, opened = sidebar()
    widget.list.emit("row-activated", row_with(widget, "New conversation"))
    assert opened.new == 1


def test_the_conversation_on_screen_is_marked() -> None:
    widget, _ = sidebar(current="ses_timer")
    assert widget.list.get_selected_row() is row_with(widget, "Build a pomodoro timer")
