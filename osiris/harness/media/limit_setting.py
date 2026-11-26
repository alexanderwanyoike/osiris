"""The person's daily picture limit, as plain text; no file means no limit."""

from __future__ import annotations

from pathlib import Path

from osiris.platform import FileSystem

LIMIT_FILE = ".config/osiris/media/daily-limit"
#: Offered when the person turns a limit on; they can change it.
SUGGESTED_LIMIT = 20


def daily_limit(files: FileSystem, home: Path) -> int | None:
    path = home / LIMIT_FILE
    if not files.exists(path):
        return None
    # Someone who wrote a limit meant to have one, so a typo must not lift it.
    try:
        text = files.read(path).strip()
        return int(text) if text.isascii() and text.isdigit() else 0
    except OSError, ValueError:
        return 0


def set_daily_limit(files: FileSystem, home: Path, images: int | None) -> None:
    if images is None:
        files.remove(home / LIMIT_FILE)
    else:
        files.write(home / LIMIT_FILE, f"{images}\n")
