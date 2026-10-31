"""A Skin's picture in a Theme: where it is kept, and when it is drawn again."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path


def picture_for(cache: Path, skin: str, theme: str, sources: Sequence[Path]) -> Path:
    """Named for what it shows, so a picture of a Skin or Theme since
    changed is not found and is drawn again."""
    return cache / skin / theme / f"{signature(sources)}.png"


def _failure(picture: Path) -> Path:
    return picture.with_suffix(".failed")


def failed(picture: Path) -> None:
    """Remember that drawing it failed, so it is not tried again until
    something it shows changes."""
    marker = _failure(picture)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()


def needs_drawing(picture: Path) -> bool:
    return not picture.is_file() and not _failure(picture).exists()


def land(picture: Path, drawer: Callable[[Path], None]) -> None:
    """Have drawer write the picture beside it, then move it in whole; each
    drawing has a file of its own, so two at once never mix."""
    picture.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(suffix=".partial.png", dir=picture.parent)
    os.close(handle)
    partial = Path(name)
    try:
        drawer(partial)
        partial.replace(picture)
    finally:
        partial.unlink(missing_ok=True)


def draw(picture: Path, drawer: Callable[[Path], None]) -> None:
    """Land the picture in place of the pictures of this Skin and Theme it
    supersedes."""
    land(picture, drawer)
    for superseded in picture.parent.iterdir():
        if superseded != picture:
            superseded.unlink(missing_ok=True)


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
