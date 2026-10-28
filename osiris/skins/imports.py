"""Import what a person downloaded for their Skins: icon sets, cursor sets,
fonts and GTK themes, from the archives they usually come in."""

from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from osiris.model.names import slug
from osiris.platform.process import CommandRunner
from osiris.skins.looks import is_cursor_set, is_icon_set
from osiris.skins.pack import LABEL_FILE, Skinpack, read
from osiris.skins.share import free_name, start_history


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

#: Sets every other set falls back to, and names too generic to be one set's.
_REFUSED_SETS = {"hicolor", "default", "locolor", "dark", "light"}


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
            if folder.name.lower() in _REFUSED_SETS:
                raise UnusableDownload(
                    f"{download.name}: a set named {folder.name} is not imported"
                )
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


#: The parts of a GTK theme a Skin shapes; the rest of a download is left out.
SURFACE_FOLDERS = ("gtk-3.0", "gtk-4.0", "cinnamon")


def import_gtk_theme(download: Path, mine: Path, runner: CommandRunner) -> Skinpack:
    """A downloaded GTK theme as a person's own Skin, worn in its own colours
    until Osiris converts them to the Theme's gaps."""
    with tempfile.TemporaryDirectory() as scratch:
        unpack(download, Path(scratch))
        themes = sorted(
            (
                folder
                for folder in Path(scratch).rglob("*")
                if (folder / "gtk-3.0" / "gtk.css").is_file()
            ),
            key=lambda folder: len(folder.name),
        )
        if not themes:
            raise UnusableDownload(f"{download.name}: no GTK theme in it")
        dark = [folder for folder in themes if "dark" in folder.name.lower()]
        light = [folder for folder in themes if folder not in dark]
        label = (light or dark)[0].name
        skin = mine / free_name(mine, slug(label))
        variants = (
            {"light": light[0], "dark": dark[0]}
            if light and dark
            else {"common": themes[0]}
        )
        for variant, theme in variants.items():
            for surface in SURFACE_FOLDERS:
                if (theme / surface).is_dir():
                    shutil.copytree(theme / surface, skin / "files" / variant / surface)
            dock = theme / "plank" / "dock.theme"
            if dock.is_file():
                for target in ("light", "dark") if variant == "common" else (variant,):
                    (skin / "plank").mkdir(parents=True, exist_ok=True)
                    shutil.copy(dock, skin / "plank" / f"dock-{target}.theme")
    (skin / LABEL_FILE).write_text(
        json.dumps(
            {
                "label": label,
                "author": "Imported",
                "version": "imported",
                "licence": "See the original download",
                "source": download.name,
            },
            indent=2,
        )
        + "\n"
    )
    start_history(skin, f"Import {download.name}", runner)
    return read(skin)
