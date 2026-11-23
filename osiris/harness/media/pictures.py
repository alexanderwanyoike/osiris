"""Generated pictures, kept as the person's own files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from osiris.harness.media.image_model import ImageModel
from osiris.harness.media.maker import ImageMaker
from osiris.harness.media.model_catalog import ModelCatalog
from osiris.harness.media.model_setting import (
    DEFAULT_MODEL,
    save_model,
    saved_model,
)
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
    catalog: ModelCatalog

    def find(self, words: str) -> list[ImageModel]:
        return self.catalog.search(words)

    def default_model(self) -> str:
        return saved_model(self.files, self.home) or DEFAULT_MODEL

    def choose(self, model: str) -> None:
        self.catalog.inputs(model)
        save_model(self.files, self.home, model)

    def make(self, description: str, model: str | None = None) -> bytes:
        return self.maker.make(description, model)

    def keep(self, name: str, data: bytes) -> Path:
        return keep_picture(self.files, self.home, name, data)
