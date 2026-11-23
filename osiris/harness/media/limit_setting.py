"""The person's daily picture limit, as plain text; no file means no limit."""

from __future__ import annotations

from pathlib import Path

from osiris.platform import FileSystem

LIMIT_FILE = ".config/osiris/media/daily-limit"


def daily_limit(files: FileSystem, home: Path) -> int | None:
    path = home / LIMIT_FILE
    return int(files.read(path).strip()) if files.exists(path) else None


def set_daily_limit(files: FileSystem, home: Path, images: int | None) -> None:
    if images is None:
        files.remove(home / LIMIT_FILE)
    else:
        files.write(home / LIMIT_FILE, f"{images}\n")
