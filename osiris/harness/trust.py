"""Whether the person has allowed the Harness everything (CONTEXT.md).

Kept as a file in their home, so the Harness and the tool server, separate
processes, read the same choice.
"""

from __future__ import annotations

from pathlib import Path

from osiris.platform import FileSystem

ALLOW_EVERYTHING = ".config/osiris/harness/allow-everything"


def allows_everything(files: FileSystem, home: Path) -> bool:
    return files.exists(home / ALLOW_EVERYTHING)


def allow_everything(files: FileSystem, home: Path, *, on: bool) -> None:
    if on:
        files.write(home / ALLOW_EVERYTHING, "")
    else:
        files.remove(home / ALLOW_EVERYTHING)
