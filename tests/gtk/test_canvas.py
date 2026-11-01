"""The Canvas: a tab for each Program a Conversation touched, its code shown
read-only, editing handed to Code (ADR 0016)."""

from __future__ import annotations

from pathlib import Path

gi = __import__("gi")
gi.require_version("Adw", "1")
from canvas import Canvas  # noqa: E402
from gi.repository import Gtk  # noqa: E402

from osiris.harness.panels import Kind  # noqa: E402
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


def titles(widget: Canvas, kind: Kind) -> list[str]:
    view = widget.views[kind]
    return [view.get_nth_page(i).get_title() for i in range(view.get_n_pages())]


def test_a_program_opens_on_its_code() -> None:
    widget, _ = canvas()
    assert code(widget) == "print('tick')\n"
    page = widget.views[Kind.CODE].get_selected_page().get_child()
    assert "pomodoro / main.py" in texts(page)


def test_editing_is_handed_to_code() -> None:
    widget, opened = canvas()
    page = widget.views[Kind.CODE].get_selected_page().get_child()
    button = next(
        w
        for w in widgets(page)
        if isinstance(w, Gtk.Button) and w.get_tooltip_text() == "Open in Code"
    )
    button.emit("clicked")
    assert opened == [(Path("/home/tester/Code/pomodoro"), Path("main.py"))]


def test_showing_other_programs_closes_the_tabs_of_those_gone() -> None:
    widget, _ = canvas()
    widget.show([(program("notes", "Notes"), [Path("main.py")])])
    assert titles(widget, Kind.CODE) == ["main.py"]
    page = widget.views[Kind.CODE].get_selected_page().get_child()
    assert "notes / main.py" in texts(page)


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
    page = widget.views[Kind.CHANGES].get_selected_page()
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
    assert titles(widget, Kind.CHANGES) == ["Changes: tidy main.py"]


def test_a_comment_on_picked_lines_reaches_thoth_with_its_file_and_lines() -> None:
    widget, comments = changed()
    buffer = widget.current_view().get_buffer()
    _, start = buffer.get_iter_at_line(3)
    _, end = buffer.get_iter_at_line(4)
    end.forward_to_line_end()
    buffer.select_range(start, end)
    entry = find(widget.views[Kind.CHANGES].get_selected_page().get_child(), Gtk.Entry)
    entry.set_text("Count down from five instead.")
    entry.emit("activate")
    assert comments == [("main.py", (11, 12), "Count down from five instead.")]
    assert entry.get_text() == ""


def test_files_sits_in_a_toolbar_at_the_top_right() -> None:
    widget, _ = canvas()
    files = next(
        w
        for w in widgets(widget.toolbar)
        if isinstance(w, Gtk.Button) and w.get_icon_name() == "folder-symbolic"
    )
    assert files.get_tooltip_text() == "Files"
    assert widget.toolbar.get_halign() is Gtk.Align.END
    assert widget.get_first_child() is widget.toolbar


def test_what_a_program_runs_opens_as_a_tab_in_the_code_group() -> None:
    widget, _ = canvas()
    assert titles(widget, Kind.CODE) == ["main.py"]
    assert code(widget) == "print('tick')\n"


def test_choosing_a_file_in_the_tree_opens_it_as_a_tab_of_its_own() -> None:
    widget, _ = canvas()
    readme = next(
        row
        for row in widgets(widget.tree)
        if isinstance(row, Gtk.ListBoxRow) and "README.md" in texts(row)
    )
    widget.tree.emit("row-activated", readme)
    assert titles(widget, Kind.CODE) == ["main.py", "README.md"]
    assert code(widget) == "# Pomodoro\n"


def test_two_groups_sit_side_by_side_with_a_line_to_resize_them() -> None:
    widget, _ = changed()
    tiled = widget._tiles.get_first_child()
    assert isinstance(tiled, Gtk.Paned)
    assert tiled.get_orientation() is Gtk.Orientation.HORIZONTAL


def test_closing_a_groups_last_tab_gives_its_room_to_the_others() -> None:
    widget, _ = changed()
    (tidy,) = widget.panels.groups[1].tabs
    widget.close(tidy)
    assert [g.kind for g in widget.panels.groups] == [Kind.CODE]
    assert not isinstance(widget._tiles.get_first_child(), Gtk.Paned)


def test_with_every_group_closed_files_opens_the_code_group_again() -> None:
    """The toolbar stays, so the files are always one click away."""
    widget, _ = canvas()
    for tab in list(widget.panels.groups[0].tabs):
        widget.close(tab)
    assert widget.panels.groups == []
    assert widget.toolbar.get_parent() is widget
    files = next(
        w
        for w in widgets(widget.toolbar)
        if isinstance(w, Gtk.Button) and w.get_icon_name() == "folder-symbolic"
    )
    files.emit("clicked")
    assert titles(widget, Kind.CODE) == ["main.py"]


def nested() -> Canvas:
    widget = Canvas(read=lambda _path: "", open_in_code=lambda _f, _p: None)
    widget.show([(program("timer", "Timer"), [Path("main.py"), Path("src/clock.py")])])
    return widget


def tree_row(widget: Canvas, name: str) -> Gtk.ListBoxRow:
    return next(
        row
        for row in widgets(widget.tree)
        if isinstance(row, Gtk.ListBoxRow) and name in texts(row)
    )


def test_a_folders_files_show_once_the_folder_is_opened() -> None:
    widget = nested()
    assert not tree_row(widget, "clock.py").get_visible()
    widget.tree.emit("row-activated", tree_row(widget, "src"))
    assert tree_row(widget, "clock.py").get_visible()
    widget.tree.emit("row-activated", tree_row(widget, "src"))
    assert not tree_row(widget, "clock.py").get_visible()


def test_each_file_and_folder_shows_an_icon_for_its_kind() -> None:
    widget = nested()
    (folder,) = [
        w for w in widgets(tree_row(widget, "src")) if isinstance(w, Gtk.Image)
    ]
    assert folder.get_icon_name() == "folder-symbolic"
    (python,) = [
        w for w in widgets(tree_row(widget, "main.py")) if isinstance(w, Gtk.Image)
    ]
    assert python.get_gicon() is not None
