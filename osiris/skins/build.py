"""Build a Skin: compile a skinpack in a Theme's colours into a GTK theme.

A skinpack is laid out by surface, one Sass entry per variant:

    sass/                       its partials; Osiris adds _gaps.scss
    gtk-3.0/gtk-<variant>.scss
    gtk-4.0/gtk-<variant>.scss          optional, like every entry below
    cinnamon/cinnamon-<variant>.scss    Osiris's own panel otherwise
    libadwaita/libadwaita-<variant>.scss
    files/common/, files/<variant>/   copied into the theme, SVG and CSS gaps filled
    plank/dock-<variant>.theme          Osiris's own dock otherwise
    rofi/launcher.rasi          optional; Osiris's own launcher theme otherwise
"""

from __future__ import annotations

import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from osiris.model.names import is_slug
from osiris.platform.process import CommandRunner
from osiris.skins.pack import (
    Skinpack,
    SkinpackError,
    fill,
    gaps,
    refuse_programs,
    sass_gaps,
)

SURFACES = (
    ("gtk-3.0/gtk", "gtk-3.0/gtk.css"),
    ("gtk-4.0/gtk", "gtk-4.0/gtk.css"),
    ("cinnamon/cinnamon", "cinnamon/cinnamon.css"),
    ("libadwaita/libadwaita", "libadwaita.css"),
)


@dataclass(frozen=True)
class Built:
    theme: str
    dock: str | None
    adwaita: Path | None
    cinnamon: bool
    launcher: str | None = None


def build(
    pack: Skinpack,
    theme: Mapping[str, Any],
    themes_dir: Path,
    work_dir: Path,
    runner: CommandRunner,
    only: Sequence[str] | None = None,
) -> Built:
    refuse_programs(pack)
    if not is_slug(theme["name"]):
        raise SkinpackError(f"{theme['name']!r} is not a Theme's name")
    filled = gaps(theme)
    variant = filled["variant"]
    # Shipped packs are read-only; the gaps are written into a copy.
    work = work_dir / pack.name
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(pack.root, work)
    (work / "sass").mkdir(exist_ok=True)
    (work / "sass" / "_gaps.scss").write_text(sass_gaps(filled))

    name = f"Osiris-{pack.name}-{theme['name']}"
    target = themes_dir / name
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    for files in (work / "files" / "common", work / "files" / variant):
        if files.is_dir():
            shutil.copytree(files, target, dirs_exist_ok=True)
    for picture in (*target.rglob("*.svg"), *target.rglob("*.css")):
        picture.write_text(_filled(picture, filled))
    if (
        not (work / f"gtk-3.0/gtk-{variant}.scss").is_file()
        and not (target / "gtk-3.0" / "gtk.css").is_file()
    ):
        raise SkinpackError(f"{pack.label}: no gtk-3.0 sheet for {variant}")
    compiled = _compile(work, target, variant, runner, only)
    (target / "index.theme").write_text(
        "[X-GNOME-Metatheme]\n"
        f"Name={name}\n"
        "Type=X-GNOME-Metatheme\n"
        f"Comment=Osiris {pack.label} in {theme['name']}\n"
        f"GtkTheme={name}\n"
        f"MetacityTheme={name}\n"
    )
    plank = work / "plank" / f"dock-{variant}.theme"
    dock = _filled(plank, filled) if plank.is_file() else None
    rofi = work / "rofi" / "launcher.rasi"
    launcher = _filled(rofi, filled) if rofi.is_file() else None
    return Built(
        theme=name,
        dock=dock,
        adwaita=target / "libadwaita.css" if "libadwaita" in compiled else None,
        cinnamon="cinnamon" in compiled
        or (target / "cinnamon" / "cinnamon.css").is_file(),
        launcher=launcher,
    )


def _compile(
    work: Path,
    target: Path,
    variant: str,
    runner: CommandRunner,
    only: Sequence[str] | None,
) -> set[str]:
    """Compile each surface's Sass entry for the variant; the surfaces done."""
    compiled = set()
    for entry, out in SURFACES:
        surface = entry.split("/")[0]
        source = work / f"{entry}-{variant}.scss"
        if not source.is_file() or (only and surface not in only):
            continue
        (target / out).parent.mkdir(parents=True, exist_ok=True)
        runner.run(
            "sassc", "-M", "-t", "expanded", str(source), str(target / out), quiet=True
        )
        compiled.add(surface)
    return compiled


def _filled(path: Path, filled: Mapping[str, str]) -> str:
    try:
        text = path.read_text()
    except UnicodeDecodeError:
        raise SkinpackError(f"{path.name} is not UTF-8 text") from None
    return fill(text, filled)
