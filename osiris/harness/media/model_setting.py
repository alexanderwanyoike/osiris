"""The image model a person has made their default, as plain text."""

from __future__ import annotations

from pathlib import Path

from osiris.platform import FileSystem

MODEL_FILE = ".config/osiris/media/image-model"


def saved_model(files: FileSystem, home: Path) -> str | None:
    path = home / MODEL_FILE
    if not files.exists(path):
        return None
    try:
        return files.read(path).strip() or None
    except OSError, ValueError:
        return None


def save_model(files: FileSystem, home: Path, model: str | None) -> None:
    if model is None:
        files.remove(home / MODEL_FILE)
    else:
        files.write(home / MODEL_FILE, f"{model}\n")
