"""The Canvas: a tab for each Program a Conversation touched, its code shown
read-only, editing handed to Code (ADR 0016)."""

from __future__ import annotations

from pathlib import Path

gi = __import__("gi")
gi.require_version("Adw", "1")
from canvas import Canvas  # noqa: E402
from gi.repository import Adw, Gtk  # noqa: E402

from osiris.programs.manifest import parse  # noqa: E402
from osiris.programs.programs import Program  # noqa: E402

from .conftest import find, texts, widgets  # noqa: E402

SOURCES = {
    "main.py": "print('tick')\n",
    "README.md": "# Pomodoro\n",
}


def program(name: str, label: str) -> Program:
    manifest = parse(
        f'{{"name": "{name}", "label": "{label}", "description": "x",'
        ' "run": ["python3", "main.py"]}'
    )
    return Program(manifest, Path("/home/tester/Code") / name, "abc", None)


def canvas() -> tuple[Canvas, list[tuple[Path, Path]]]:
    opened: list[tuple[Path, Path]] = []
    widget = Canvas(
        read=lambda path: SOURCES[path.name],
        open_in_code=lambda folder, file: opened.append((folder, file)),
    )
    widget.show(
        [
            (program("pomodoro", "Pomodoro"), [Path("README.md"), Path("main.py")]),
            (program("notes", "Notes"), [Path("main.py")]),
        ]
    )
    return widget, opened


def code(widget: Canvas) -> str:
    view = widget.current_view()
    buffer = view.get_buffer()
    return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)


def test_each_program_has_a_tab() -> None:
    widget, _ = canvas()
    titles = [
        widget.tabs.get_nth_page(i).get_title()
        for i in range(widget.tabs.get_n_pages())
    ]
    assert titles == ["Pomodoro", "Notes"]


def test_a_program_opens_on_its_code() -> None:
    widget, _ = canvas()
    assert code(widget) == "print('tick')\n"
    assert "pomodoro / main.py" in texts(widget.tabs.get_selected_page().get_child())


def test_choosing_a_file_in_the_tree_shows_it() -> None:
    widget, _ = canvas()
    page = widget.tabs.get_selected_page().get_child()
    tree = next(w for w in widgets(page) if isinstance(w, Gtk.ListBox))
    readme = next(
        row
        for row in widgets(tree)
        if isinstance(row, Gtk.ListBoxRow) and "README.md" in texts(row)
    )
    tree.emit("row-activated", readme)
    assert code(widget) == "# Pomodoro\n"


def test_editing_is_handed_to_code() -> None:
    widget, opened = canvas()
    page = widget.tabs.get_selected_page().get_child()
    button = next(
        w
        for w in widgets(page)
        if isinstance(w, Gtk.Button) and w.get_tooltip_text() == "Open in Code"
    )
    button.emit("clicked")
    assert opened == [(Path("/home/tester/Code/pomodoro"), Path("main.py"))]


def test_the_strip_ends_with_a_list_of_every_tab() -> None:
    widget, _ = canvas()
    assert isinstance(widget.strip, Adw.TabBar)
    find(widget, Gtk.MenuButton)
