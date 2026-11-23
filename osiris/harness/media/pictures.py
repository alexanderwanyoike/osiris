"""Generated pictures, kept as the person's own files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from osiris.harness.media.maker import ImageMaker
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


@dataclass(frozen=True)
class Pictures:
    """Where the tool server's pictures come from and where they are kept."""

    maker: ImageMaker
    files: FileSystem
    home: Path

    def make(self, description: str, model: str | None = None) -> bytes:
        return self.maker.make(description, model)

    def keep(self, name: str, data: bytes) -> Path:
        return keep_picture(self.files, self.home, name, data)
