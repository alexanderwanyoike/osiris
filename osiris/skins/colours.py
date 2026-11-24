"""Fixed colours: colours written into a person's Skin rather than taken from
the Theme, so they stay the same whatever Theme is worn."""

from __future__ import annotations

from pathlib import Path


def fixed_colours(skin: Path, style: Path | None) -> list[str]:
    raise NotImplementedError
