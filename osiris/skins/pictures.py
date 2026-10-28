"""When a Skin's picture must be drawn again."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path


def picture_for(cache: Path, skin: str, theme: str) -> Path:
    return cache / f"{skin}--{theme}.png"


def _newest(source: Path) -> float:
    if source.is_dir():
        return max((_newest(child) for child in source.iterdir()), default=0.0)
    return source.stat().st_mtime if source.exists() else 0.0


def is_fresh(picture: Path, sources: Sequence[Path]) -> bool:
    """Drawn after the last change to anything it shows."""
    if not picture.is_file():
        return False
    return picture.stat().st_mtime >= max(map(_newest, sources), default=0.0)


def _failure(picture: Path) -> Path:
    return picture.with_suffix(".failed")


def failed(picture: Path) -> None:
    """Remember that drawing it failed, so it is not tried again until
    something it shows changes."""
    marker = _failure(picture)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()


def needs_drawing(picture: Path, sources: Sequence[Path]) -> bool:
    return not is_fresh(picture, sources) and not is_fresh(_failure(picture), sources)
