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
        self.new_in: list[Path] = []
        self.archived: list[str] = []
        self.deleted: list[tuple[str, str]] = []


def sidebar(
    current: str | None = None, running: frozenset[str] = frozenset()
) -> tuple[Sidebar, Opened]:
    opened = Opened()
    widget = Sidebar(
        on_open=opened.sessions.append,
        on_new=lambda: _new(opened),
        on_new_in=opened.new_in.append,
        on_archive=opened.archived.append,
        on_delete=lambda session, title: opened.deleted.append((session, title)),
    )
    widget.show_history([PROJECT], [THEME], current, running)
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


def button(root: Gtk.Widget, tooltip: str) -> Gtk.Button:
    return next(
        w
        for w in widgets(root)
        if isinstance(w, Gtk.Button) and w.get_tooltip_text() == tooltip
    )


def labelled(root: Gtk.Widget, label: str) -> Gtk.Button:
    return next(
        w for w in widgets(root) if isinstance(w, Gtk.Button) and w.get_label() == label
    )


def test_a_conversation_can_be_started_in_a_project() -> None:
    widget, opened = sidebar()
    button(row_with(widget, "pomodoro"), "New conversation in pomodoro").emit("clicked")
    assert opened.new_in == [HOME / "Code" / "pomodoro"]


def test_a_conversation_can_be_archived() -> None:
    widget, opened = sidebar()
    row = row_with(widget, "Make me a calm theme")
    next(
        w
        for w in widgets(row)
        if isinstance(w, Gtk.Button) and w.get_label() == "Archive"
    ).emit("clicked")
    assert opened.archived == ["ses_theme"]


def test_a_conversation_can_be_deleted() -> None:
    widget, opened = sidebar()
    row = row_with(widget, "Make me a calm theme")
    next(
        w
        for w in widgets(row)
        if isinstance(w, Gtk.Button) and w.get_label() == "Delete…"
    ).emit("clicked")
    assert opened.deleted == [("ses_theme", "Make me a calm theme")]


def working(row: Gtk.Widget) -> bool:
    return any(w.has_css_class("harness-running") for w in widgets(row))


def test_a_conversation_still_working_says_so() -> None:
    widget, _ = sidebar(running=frozenset({"ses_timer"}))
    assert working(row_with(widget, "Build a pomodoro timer"))
    assert not working(row_with(widget, "Make me a calm theme"))
