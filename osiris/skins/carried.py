"""Install what a skinpack carries besides style sheets: icon sets, cursors
(both icon themes to GTK) and fonts."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path

from osiris.skins.pack import Skinpack

#: In each set Osiris installed: the Skin and version it came from. A set
#: without one is someone else's and is never replaced.
STAMP = ".osiris-skin"


def install(
    pack: Skinpack,
    icons_dir: Path,
    fonts_dir: Path,
    system_icons: Sequence[Path] = (),
) -> bool:
    """Install what is not there yet; True when fonts were added."""
    stamp = f"{pack.name} {pack.version}\n"
    carried = pack.root / "icons"
    if carried.is_dir():
        for theme in sorted(carried.iterdir()):
            target = icons_dir / theme.name
            if (
                theme.is_dir()
                and not any((folder / theme.name).exists() for folder in system_icons)
                and (not target.exists() or _stamp(target) not in (None, stamp))
            ):
                _replace(theme, target, stamp)
    fonts = pack.root / "fonts"
    target = fonts_dir / pack.name
    if not fonts.is_dir() or target.exists():
        return False
    shutil.copytree(fonts, target)
    return True


def _stamp(installed: Path) -> str | None:
    try:
        return (installed / STAMP).read_text()
    except OSError:
        return None


def _replace(source: Path, target: Path, stamp: str) -> None:
    """Copy beside the old one first, so a failed copy leaves it in place."""
    staging = target.with_name(f".{target.name}.new")
    shutil.rmtree(staging, ignore_errors=True)
    shutil.copytree(source, staging)
    (staging / STAMP).write_text(stamp)
    shutil.rmtree(target, ignore_errors=True)
    staging.rename(target)
