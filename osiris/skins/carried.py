"""Install what a skinpack carries besides style sheets: icon sets, cursors
(both icon themes to GTK) and fonts."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path

from osiris.skins.pack import Skinpack


def install(
    pack: Skinpack,
    icons_dir: Path,
    fonts_dir: Path,
    system_icons: Sequence[Path] = (),
) -> bool:
    """Install what is not there yet; True when fonts were added."""
    carried = pack.root / "icons"
    if carried.is_dir():
        for theme in sorted(carried.iterdir()):
            if theme.is_dir() and not any(
                (folder / theme.name).exists() for folder in (icons_dir, *system_icons)
            ):
                shutil.copytree(theme, icons_dir / theme.name)
    fonts = pack.root / "fonts"
    target = fonts_dir / pack.name
    if not fonts.is_dir() or target.exists():
        return False
    shutil.copytree(fonts, target)
    return True
