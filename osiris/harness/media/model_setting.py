"""The image model a person has made their default, as plain text."""

from __future__ import annotations

from pathlib import Path

from osiris.platform import FileSystem

MODEL_FILE = ".config/osiris/media/image-model"
#: Used until the person chooses another; the catalog still has to offer it.
DEFAULT_IMAGE_MODEL = "fal-ai/flux/schnell"


def saved_model(files: FileSystem, home: Path) -> str | None:
    path = home / MODEL_FILE
    if not files.exists(path):
        return None
    try:
        return files.read(path).strip() or None
    except OSError, ValueError:
        return None


def save_model(files: FileSystem, home: Path, model: str) -> None:
    files.write(home / MODEL_FILE, f"{model}\n")
