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


def test_showing_again_replaces_the_tabs() -> None:
    widget, _ = canvas()
    widget.show([(program("notes", "Notes"), [Path("main.py")])])
    titles = [
        widget.tabs.get_nth_page(i).get_title()
        for i in range(widget.tabs.get_n_pages())
    ]
    assert titles == ["Notes"]


PATCH = (
    "@@ -10,3 +10,4 @@\n"
    " def tick():\n"
    "-    return 1\n"
    "+    left -= 1\n"
    "+    return left\n"
    " \n"
)


def changed() -> tuple[Canvas, list[tuple[str, tuple[int, int], str]]]:
    from osiris.harness.engine import FileChange

    comments: list[tuple[str, tuple[int, int], str]] = []
    widget, _ = canvas()
    widget.show_changes(
        "tidy main.py",
        (
            FileChange("main.py", "modified", 2, 1, PATCH),
            FileChange("notes.md", "added", 1, 0, "@@ -0,0 +1 @@\n+hello\n"),
        ),
        on_comment=lambda path, lines, text: comments.append((path, lines, text)),
    )
    return widget, comments


def test_a_questions_changes_open_in_a_tab_of_their_own() -> None:
    widget, _ = changed()
    page = widget.tabs.get_selected_page()
    assert page.get_title() == "Changes: tidy main.py"
    shown = texts(page.get_child())
    assert "main.py" in shown and "notes.md" in shown
    assert "+2 \u22121" in shown  # a minus sign, as the Canvas draws it


def test_the_first_file_opens_on_its_diff_in_the_themes_code_colours() -> None:
    widget, _ = changed()
    assert code(widget) == PATCH
    language = widget.current_view().get_buffer().get_language()
    assert language is not None and language.get_id() == "diff"


def test_showing_the_programs_again_keeps_the_changes_tab() -> None:
    widget, _ = changed()
    widget.show([(program("pomodoro", "Pomodoro"), [Path("main.py")])])
    titles = [
        widget.tabs.get_nth_page(i).get_title()
        for i in range(widget.tabs.get_n_pages())
    ]
    assert "Changes: tidy main.py" in titles


def test_a_comment_on_picked_lines_reaches_thoth_with_its_file_and_lines() -> None:
    widget, comments = changed()
    buffer = widget.current_view().get_buffer()
    _, start = buffer.get_iter_at_line(3)
    _, end = buffer.get_iter_at_line(4)
    end.forward_to_line_end()
    buffer.select_range(start, end)
    entry = find(widget.tabs.get_selected_page().get_child(), Gtk.Entry)
    entry.set_text("Count down from five instead.")
    entry.emit("activate")
    assert comments == [("main.py", (11, 12), "Count down from five instead.")]
    assert entry.get_text() == ""
