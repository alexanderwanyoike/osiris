"""A terminal in the Canvas's terminal group (#196): VTE running the person's
shell in a Program's folder, in the Theme's terminal colours and font."""

from __future__ import annotations

import time
from pathlib import Path

from gi.repository import GLib

THEME = {
    "colors": {
        "background": "#2e3440",
        "foreground": "#d8dee9",
        "accent": "#88c0d0",
    },
    "terminal": {
        **{f"regular{n}": f"#10101{n}" for n in range(8)},
        **{f"bright{n}": f"#20202{n}" for n in range(8)},
    },
    "ui": {"mono": "DejaVu Sans Mono"},
}


def started(folder: Path):
    from terminal import Terminal

    shell = Terminal(folder, THEME)
    context = GLib.MainContext.default()
    deadline = time.monotonic() + 10
    while shell.pid is None and time.monotonic() < deadline:
        context.iteration(False)
    return shell


def test_the_persons_shell_starts_in_the_programs_folder(tmp_path: Path) -> None:
    shell = started(tmp_path)
    assert shell.pid is not None
    assert Path(f"/proc/{shell.pid}/cwd").readlink() == tmp_path
    shell.close()


def test_it_is_drawn_in_the_themes_terminal_font_and_background(
    tmp_path: Path,
) -> None:
    shell = started(tmp_path)
    assert shell.get_font().get_family() == "DejaVu Sans Mono"
    background = shell.get_color_background_for_draw()
    assert background.to_string() == "rgb(46,52,64)"
    shell.close()


def test_closing_it_ends_the_shell(tmp_path: Path) -> None:
    """GLib reaps the shell; the main loop turns until it has."""
    shell = started(tmp_path)
    pid = shell.pid
    shell.close()
    context = GLib.MainContext.default()
    deadline = time.monotonic() + 5
    while Path(f"/proc/{pid}").exists() and time.monotonic() < deadline:
        context.iteration(False)
    assert not Path(f"/proc/{pid}").exists()
