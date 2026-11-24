"""Fixed colours: colours written into a person's Skin rather than taken from
the Theme, so they stay the same whatever Theme is worn."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

_SHEETS = {".scss", ".css", ".svg", ".rasi"}
# A hex colour, but not an SVG reference such as url(#fade).
_HEX = r"(?<!url\()#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b"
# Numbers only: rgba($gap-foreground, 0.1) fades a Theme colour.
_NUMBERS = r"\brgba?\(\s*[0-9][0-9.,%/\s]*\)"
_COLOUR = re.compile(f"{_HEX}|{_NUMBERS}")
#: Named per sheet; an imported theme can hold hundreds.
SHOWN = 3


def fixed_colours(skin: Path, style: Path | None) -> list[str]:
    """Each style sheet of the Skin with the colours written into it that the
    Skin it was made from does not have."""
    known = {colour for sheet in _sheets(style) for colour in _colours(sheet)}
    found = []
    for sheet in _sheets(skin):
        new = [colour for colour in _colours(sheet) if colour not in known]
        if new:
            found.append(f"{sheet.relative_to(skin).as_posix()}: {_listed(new)}")
    return found


def _sheets(root: Path | None) -> Iterator[Path]:
    if root is None:
        return
    for path in sorted(root.rglob("*")):
        if path.suffix in _SHEETS and ".git" not in path.relative_to(root).parts:
            yield path


def _colours(sheet: Path) -> list[str]:
    text = sheet.read_text(errors="replace")
    return list(dict.fromkeys(match.lower() for match in _COLOUR.findall(text)))


def _listed(colours: list[str]) -> str:
    shown = ", ".join(colours[:SHOWN])
    rest = len(colours) - SHOWN
    return f"{shown} and {rest} more" if rest > 0 else shown
