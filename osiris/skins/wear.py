"""Wear a Skin: install what it carries, then build it in a Theme's colours."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from osiris.platform.process import CommandError, CommandRunner
from osiris.skins import carried
from osiris.skins.build import Built, build
from osiris.skins.pack import Look, Skinpack, SkinpackError


@dataclass(frozen=True)
class Places:
    themes: Path
    work: Path
    icons: Path
    fonts: Path


def wear(
    pack: Skinpack,
    theme: Mapping[str, Any],
    places: Places,
    runner: CommandRunner,
    panel: Callable[[Path], None],
) -> tuple[Built, Look]:
    """Build the Skin; `panel` gives a theme folder Osiris's own panel when the
    Skin brings none. Any failure is a SkinpackError."""
    try:
        if carried.install(pack, places.icons, places.fonts):
            runner.run("fc-cache", "-f", str(places.fonts), check=False, quiet=True)
        built = build(pack, theme, places.themes, places.work, runner)
        if not built.cinnamon:
            panel(places.themes / built.theme)
    except (CommandError, OSError) as error:
        raise SkinpackError(f"{pack.label}: {error}") from error
    return built, pack.look("dark" if theme.get("dark", True) else "light")
