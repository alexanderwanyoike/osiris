"""Build a Skin: compile a skinpack in a Theme's colours into a GTK theme.

A skinpack is laid out by surface, one Sass entry per variant:

    sass/                       its partials; Osiris adds _gaps.scss
    gtk-3.0/gtk-<variant>.scss
    gtk-4.0/gtk-<variant>.scss
    cinnamon/cinnamon-<variant>.scss
    libadwaita/libadwaita-<variant>.scss
    files/common/, files/<variant>/   copied into the theme, SVG gaps filled
    plank/dock-<variant>.theme
"""

from __future__ import annotations

import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from osiris.platform.process import CommandRunner
from osiris.skins.pack import Skinpack, fill, gaps, sass_gaps

SURFACES = (
    ("gtk-3.0/gtk", "gtk-3.0/gtk.css"),
    ("gtk-4.0/gtk", "gtk-4.0/gtk.css"),
    ("cinnamon/cinnamon", "cinnamon/cinnamon.css"),
    ("libadwaita/libadwaita", "libadwaita.css"),
)


@dataclass(frozen=True)
class Built:
    theme: str
    dock: str
    adwaita: Path


def build(
    pack: Skinpack,
    theme: Mapping[str, Any],
    themes_dir: Path,
    work_dir: Path,
    runner: CommandRunner,
) -> Built:
    filled = gaps(theme)
    variant = filled["variant"]
    # Shipped packs are read-only; the gaps are written into a copy.
    work = work_dir / pack.name
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(pack.root, work)
    (work / "sass" / "_gaps.scss").write_text(sass_gaps(filled))

    name = f"Osiris-{pack.name}-{theme['name']}"
    target = themes_dir / name
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    for files in (work / "files" / "common", work / "files" / variant):
        if files.is_dir():
            shutil.copytree(files, target, dirs_exist_ok=True)
    for svg in target.rglob("*.svg"):
        svg.write_text(fill(svg.read_text(), filled))
    for entry, out in SURFACES:
        (target / out).parent.mkdir(parents=True, exist_ok=True)
        source = work / f"{entry}-{variant}.scss"
        runner.run(
            "sassc", "-M", "-t", "expanded", str(source), str(target / out), quiet=True
        )
    (target / "index.theme").write_text(
        "[X-GNOME-Metatheme]\n"
        f"Name={name}\n"
        "Type=X-GNOME-Metatheme\n"
        f"Comment=Osiris {pack.label} in {theme['name']}\n"
        f"GtkTheme={name}\n"
        f"MetacityTheme={name}\n"
    )
    dock = fill((work / "plank" / f"dock-{variant}.theme").read_text(), filled)
    return Built(theme=name, dock=dock, adwaita=target / "libadwaita.css")
