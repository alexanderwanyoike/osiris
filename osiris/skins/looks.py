"""The icon sets and cursor sets installed, which the Skin editor offers."""

from __future__ import annotations

import configparser
from collections.abc import Callable, Sequence
from pathlib import Path

#: Present everywhere as a fallback, never a look of its own.
_FALLBACKS = {"hicolor", "default", "locolor"}


def _index(folder: Path) -> configparser.SectionProxy | None:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        parser.read(folder / "index.theme")
    except configparser.Error, UnicodeDecodeError:
        return None
    return parser["Icon Theme"] if parser.has_section("Icon Theme") else None


def _themes(folders: Sequence[Path], wanted: Callable[[Path], bool]) -> list[str]:
    found: set[str] = set()
    for root in folders:
        if not root.is_dir():
            continue
        for folder in root.iterdir():
            if folder.is_dir() and folder.name not in _FALLBACKS and wanted(folder):
                found.add(folder.name)
    return sorted(found, key=str.lower)


def is_icon_set(folder: Path) -> bool:
    index = _index(folder)
    return (
        index is not None
        and bool(index.get("Directories", "").strip())
        and index.get("Hidden", "false").lower() != "true"
    )


def icon_themes(folders: Sequence[Path]) -> list[str]:
    return _themes(folders, is_icon_set)


def is_cursor_set(folder: Path) -> bool:
    return (folder / "cursors").is_dir()


def cursor_themes(folders: Sequence[Path]) -> list[str]:
    return _themes(folders, is_cursor_set)
