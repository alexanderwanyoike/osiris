"""A Skin is data only: what may be in one, and what Osiris refuses (ADR 0019).

Osiris builds a Skin itself from style sheets, pictures and settings; a Skin
that brings a program would have it run as the person, unseen.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Style sheets, pictures, settings, fonts and the text that credits them.
DATA_SUFFIXES = {
    ".scss", ".css", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".xpm",
    ".json", ".theme", ".rasi", ".ini", ".xml",
    ".ttf", ".otf", ".ttc", ".woff", ".woff2",
    ".md", ".txt",
}  # fmt: skip
#: Files with no suffix that are text: licences and credits.
DATA_NAMES = {"LICENSE", "COPYING", "AUTHORS", "CREDITS", "NOTICE", "README"}
#: Cursor files carry no suffix; they are known by their first bytes.
_XCURSOR = b"Xcur"


def problems(root: Path) -> list[str]:
    """Why the Skin at root is not data only; empty when it is."""
    found = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if relative.parts[0] == ".git":
            continue
        shown = relative.as_posix()
        if path.is_symlink():
            if not path.resolve().is_relative_to(root.resolve()):
                found.append(f"{shown} links outside the Skin")
            continue
        if path.is_dir():
            continue
        if os.access(path, os.X_OK):
            found.append(f"{shown} may not be executable")
        elif not is_data(path, relative):
            found.append(f"{shown} is not part of a Skin")
    return found


def is_data(path: Path, relative: Path) -> bool:
    if path.suffix.lower() in DATA_SUFFIXES or path.name in DATA_NAMES:
        return True
    if "cursors" in relative.parts[:-1]:
        with path.open("rb") as file:
            return file.read(4) == _XCURSOR
    return False
