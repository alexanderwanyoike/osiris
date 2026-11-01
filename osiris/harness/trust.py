"""Whether the person has turned on auto mode (CONTEXT.md).

Kept as a file in their home, so the Harness and the tool server, separate
processes, read the same choice.
"""

from __future__ import annotations

from pathlib import Path

from osiris.platform import FileSystem

#: Named for what auto mode replaced, so a person who had it on stays in it.
AUTO_MODE = ".config/osiris/harness/allow-everything"


def auto_mode_on(files: FileSystem, home: Path) -> bool:
    return files.exists(home / AUTO_MODE)


def turn_auto_mode(files: FileSystem, home: Path, *, on: bool) -> None:
    if on:
        files.write(home / AUTO_MODE, "")
    else:
        files.remove(home / AUTO_MODE)
