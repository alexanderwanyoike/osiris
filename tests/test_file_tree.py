"""A Program's files as the Canvas's tree shows them (#198): folders that open
and close, folders before files, each in name order."""

from __future__ import annotations

from pathlib import Path

from osiris.harness.file_tree import Node, tree


def test_files_are_nested_in_their_folders_with_folders_first() -> None:
    paths = [
        Path("main.py"),
        Path("src/timer.py"),
        Path("README.md"),
        Path("src/ui/window.py"),
    ]
    assert tree(paths) == (
        Node(
            "src",
            Path("src"),
            (
                Node(
                    "ui", Path("src/ui"), (Node("window.py", Path("src/ui/window.py")),)
                ),
                Node("timer.py", Path("src/timer.py")),
            ),
        ),
        Node("main.py", Path("main.py")),
        Node("README.md", Path("README.md")),
    )
