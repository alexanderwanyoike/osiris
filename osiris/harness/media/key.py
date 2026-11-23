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
    return _clean(files.read(path)) or None if files.exists(path) else None


def save_fal_key(files: FileSystem, home: Path, key: str) -> None:
    files.write(home / KEY_FILE, f"{_clean(key)}\n", mode=0o600)


def remove_fal_key(files: FileSystem, home: Path) -> None:
    files.remove(home / KEY_FILE)


def _clean(key: str) -> str:
    # A control character in a request header gets the whole request refused.
    return "".join(c for c in key if c.isprintable()).strip()
