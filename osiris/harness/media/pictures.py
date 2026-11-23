"""Generated pictures, kept as the person's own files."""

from __future__ import annotations

from pathlib import Path

from osiris.platform import FileSystem

PICTURES = "Pictures/Osiris"


def keep_picture(files: FileSystem, home: Path, name: str, data: bytes) -> Path:
    folder = home / PICTURES
    path = folder / f"{name}.png"
    number = 2
    while files.exists(path):
        path = folder / f"{name}-{number}.png"
        number += 1
    files.write_bytes(path, data)
    return path
