"""Import what a person downloaded for their Skins: icon sets, cursor sets,
fonts and GTK themes, from the archives they usually come in."""

from __future__ import annotations

import json
import posixpath
import shutil
import tarfile
import tempfile
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath

from osiris.model.names import slug
from osiris.platform.process import CommandRunner
from osiris.skins.check import is_data
from osiris.skins.looks import FALLBACKS, is_cursor_set, is_icon_set
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


def copy_data(source: Path, target: Path) -> None:
    """Copy what is a Skin's data under source, without exec bits, and the
    links that stay inside it, as links."""
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(part.startswith(".") for part in relative.parts):
            continue
        copied = target / relative
        if path.is_symlink():
            points_to = path.readlink()
            reach = posixpath.normpath((relative.parent / points_to).as_posix())
            if not points_to.is_absolute() and not reach.startswith(".."):
                copied.parent.mkdir(parents=True, exist_ok=True)
                copied.symlink_to(points_to)
        elif path.is_file() and is_data(path, relative):
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, copied)


FONT_SUFFIXES = {".ttf", ".otf", ".ttc"}

#: Names too generic to be one set's.
_REFUSED_SETS = {*FALLBACKS, "dark", "light"}


ARCHIVE_SUFFIXES = (".tar.gz", ".tar.xz", ".tar.bz2", ".tgz", ".txz", ".tar", ".zip")


def _stem(download: Path) -> str:
    for suffix in ARCHIVE_SUFFIXES:
        if download.name.lower().endswith(suffix):
            return download.name[: -len(suffix)]
    return download.stem


SYSTEM_ICONS = Path("/usr/share/icons")


def install_sets(
    download: Path, icons_dir: Path, system: Sequence[Path] = (SYSTEM_ICONS,)
) -> list[str]:
    """Install every icon or cursor set inside a download; their names."""
    with tempfile.TemporaryDirectory() as scratch:
        # Inside a folder named after the download, a set packed at the root of
        # its archive is found like any other.
        unpack(download, Path(scratch) / _stem(download))
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
            if any((root / folder.name).exists() for root in system):
                raise UnusableDownload(
                    f"{download.name}: {folder.name} is installed with the system"
                )
        icons_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=icons_dir, prefix=".import-") as staging:
            new, replaced = Path(staging) / "new", Path(staging) / "replaced"
            replaced.mkdir()
            for folder in found:
                copy_data(folder, new / folder.name)
            for folder in found:
                target = icons_dir / folder.name
                if target.exists() or target.is_symlink():
                    target.rename(replaced / folder.name)
                (new / folder.name).rename(target)
        return sorted(folder.name for folder in found)


def _is_font(path: Path, unpacked: Path) -> bool:
    hidden = (
        part.startswith(".") or part == "__MACOSX"
        for part in path.relative_to(unpacked).parts
    )
    return path.suffix.lower() in FONT_SUFFIXES and path.is_file() and not any(hidden)


def _unused(font: Path, taken: Sequence[str]) -> str:
    name, number = font.name, 2
    while name in taken:
        name, number = f"{font.stem}-{number}{font.suffix}", number + 1
    return name


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
                fonts = [font for font in into.rglob("*") if _is_font(font, into)]
            for font in fonts:
                name = _unused(font, installed)
                shutil.copy(font, fonts_dir / name)
                installed.append(name)
    if not installed:
        raise UnusableDownload("no font in what was given")
    return sorted(installed)


#: The parts of a GTK theme a Skin shapes; the rest of a download is left out.
SURFACE_FOLDERS = ("gtk-3.0", "gtk-4.0", "cinnamon")


def _base(name: str) -> str:
    return name[: -len("-dark")] if name.lower().endswith("-dark") else name


def _variants(themes: Mapping[str, Path]) -> dict[str, Path]:
    """The theme with the shortest name, its colour variants left out: its
    light and dark if it has both, otherwise the one it has for both."""
    base = min({_base(name) for name in themes}, key=lambda name: (len(name), name))
    named = [folder for name, folder in themes.items() if _base(name) == base]
    light = themes.get(base)
    dark = next((folder for folder in named if folder.name != base), None)
    if light and dark:
        return {"light": light, "dark": dark}
    return {"common": named[0]}


def _lay_out(theme: Path, variant: str, skin: Path) -> None:
    files = skin / "files" / variant
    for surface in SURFACE_FOLDERS:
        if (theme / surface).is_dir():
            copy_data(theme / surface, files / surface)
    # A theme's GTK 4 sheet is written for libadwaita, as its own installers
    # put it in ~/.config/gtk-4.0; its pictures stay where it names them.
    if (files / "gtk-4.0" / "gtk.css").is_file():
        (files / "gtk-4.0" / "gtk.css").rename(files / "libadwaita.css")
    dock = theme / "plank" / "dock.theme"
    if dock.is_file():
        for target in ("light", "dark") if variant == "common" else (variant,):
            (skin / "plank").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(dock, skin / "plank" / f"dock-{target}.theme")


def import_gtk_theme(download: Path, mine: Path, runner: CommandRunner) -> Skinpack:
    """A downloaded GTK theme as a person's own Skin, worn in its own colours
    until Osiris converts them to the Theme's gaps."""
    with tempfile.TemporaryDirectory() as scratch:
        unpack(download, Path(scratch))
        themes = {
            folder.name: folder
            for folder in sorted(Path(scratch).rglob("*"))
            if (folder / "gtk-3.0" / "gtk.css").is_file()
        }
        if not themes:
            raise UnusableDownload(f"{download.name}: no GTK theme in it")
        variants = _variants(themes)
        label = next(iter(variants.values())).name
        skin = mine / free_name(mine, slug(label))
        try:
            for variant, theme in variants.items():
                _lay_out(theme, variant, skin)
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
        except BaseException:
            shutil.rmtree(skin, ignore_errors=True)
            raise
