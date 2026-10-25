"""Import what a person downloaded for their Skins: icon sets, cursor sets,
fonts and GTK themes, from the archives they usually come in."""

from __future__ import annotations

import shutil
import tarfile
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from osiris.skins.looks import is_cursor_set, is_icon_set


class UnusableDownload(ValueError):
    """A download that cannot be imported, and why."""


def unpack(download: Path, into: Path) -> None:
    """Unpack a zip or tar archive, refusing members that reach outside."""
    into.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(download):
        with zipfile.ZipFile(download) as archive:
            for name in archive.namelist():
                parts = PurePosixPath(name).parts
                if PurePosixPath(name).is_absolute() or ".." in parts:
                    raise UnusableDownload(f"{download.name}: {name} reaches outside")
            archive.extractall(into)
        return
    try:
        with tarfile.open(download) as archive:
            archive.extractall(into, filter="data")
    except (tarfile.TarError, OSError) as error:
        raise UnusableDownload(f"{download.name}: {error}") from None


FONT_SUFFIXES = {".ttf", ".otf", ".ttc"}


def install_sets(download: Path, icons_dir: Path) -> list[str]:
    """Install every icon or cursor set inside a download; their names."""
    with tempfile.TemporaryDirectory() as scratch:
        unpack(download, Path(scratch))
        found = [
            folder
            for folder in sorted(Path(scratch).rglob("*"))
            if folder.is_dir() and (is_icon_set(folder) or is_cursor_set(folder))
        ]
        if not found:
            raise UnusableDownload(f"{download.name}: no icon or cursor set in it")
        for folder in found:
            target = icons_dir / folder.name
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(folder, target)
        return sorted(folder.name for folder in found)


def install_fonts(downloads: Sequence[Path], fonts_dir: Path) -> list[str]:
    """Install the fonts given, or inside the archives given; their file names."""
    installed: list[str] = []
    fonts_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as scratch:
        for number, download in enumerate(downloads):
            if download.suffix.lower() in FONT_SUFFIXES:
                fonts = [download]
            else:
                into = Path(scratch) / str(number)
                try:
                    unpack(download, into)
                except UnusableDownload:
                    continue
                fonts = [
                    f for f in into.rglob("*") if f.suffix.lower() in FONT_SUFFIXES
                ]
            for font in fonts:
                shutil.copy(font, fonts_dir / font.name)
                installed.append(font.name)
    if not installed:
        raise UnusableDownload("no font in what was given")
    return sorted(installed)
