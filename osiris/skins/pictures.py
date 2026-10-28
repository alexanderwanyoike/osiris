"""When a Skin's picture must be drawn again."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator, Mapping, Sequence
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


def cursor_picture(cache: Path, cursor: str, shape: str) -> Path:
    """Where one shape of a cursor theme is drawn; the name comes from a
    Skin's look, which anyone may have written."""
    if not cursor or "/" in cursor or cursor in (".", ".."):
        raise ValueError(f"{cursor!r} is not the name of a cursor theme")
    return cache / f"cursor-{cursor}-{shape}.png"


#: What the XDG base directory spec says to assume when it is unset.
_DATA_DIRS = "/usr/local/share:/usr/share"


def sampler_env(environ: Mapping[str, str], themes_root: Path) -> dict[str, str]:
    """The sampler's environment: GTK finds a theme by name under any data
    folder's themes/, and the person's own folder keeps its icons and fonts."""
    dirs = environ.get("XDG_DATA_DIRS") or _DATA_DIRS
    return {**environ, "XDG_DATA_DIRS": f"{themes_root}:{dirs}"}


def _files(source: Path) -> Iterator[Path]:
    if source.is_file():
        yield source
    elif source.is_dir():
        for child in sorted(source.iterdir()):
            if child.name != ".git":
                yield from _files(child)


def signature(sources: Sequence[Path]) -> str:
    """The names and contents of everything a picture shows; a Skin's
    history is not shown."""
    digest = hashlib.sha256()
    for source in sources:
        for path in _files(source):
            digest.update(str(path.relative_to(source.parent)).encode() + b"\0")
            content = path.read_bytes()
            digest.update(len(content).to_bytes(8) + content)
    return digest.hexdigest()[:16]
