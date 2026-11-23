"""The person's FAL key, in a file only they can read.

A file rather than the Engine's accounts, because FAL is a media Provider the
Engine does not know, and the tool server is a separate process that needs it.
"""

from __future__ import annotations

from pathlib import Path

from osiris.platform import FileSystem

KEY_FILE = ".config/osiris/media/fal-key"


def fal_key(files: FileSystem, home: Path) -> str | None:
    path = home / KEY_FILE
    return files.read(path).strip() or None if files.exists(path) else None


def save_fal_key(files: FileSystem, home: Path, key: str) -> None:
    files.write(home / KEY_FILE, f"{key}\n", mode=0o600)
