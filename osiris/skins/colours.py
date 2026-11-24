"""Fixed colours: colours written into a person's Skin rather than taken from
the Theme, so they stay the same whatever Theme is worn."""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from pathlib import Path

_SHEETS = {".scss", ".css", ".svg", ".rasi"}
# Hex-shaped text that is not a colour: references, links and entities.
_NOT_COLOURS = re.compile(r"url\([^)]*\)|href=(?:\"[^\"]*\"|'[^']*')|&#\w+;")
# Not a selector such as &#add-color-button or #cafe-box.
_HEX = r"(?<![&\w])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])"
# Numbers only: rgba($gap-foreground, 0.1) fades a Theme colour.
_NUMBERS = r"\brgba?\(\s*[0-9][0-9.,%/\s]*\)"
_COLOUR = re.compile(f"{_HEX}|{_NUMBERS}")
# How many colours per sheet and how many sheets are named; a downloaded
# theme can hold hundreds of each.
_SHOWN = 3
_SHEETS_SHOWN = 10


def fixed_colours(skin: Path, originals: Sequence[Path]) -> list[str]:
    """Each style sheet of the Skin with the colours written into it that none
    of the Skins it was made from have."""
    known = {
        value
        for original in originals
        for sheet in _sheets(original)
        for value in _colours(sheet)
    }
    found = []
    for sheet in _sheets(skin):
        new = [shown for value, shown in _colours(sheet).items() if value not in known]
        if new:
            found.append(f"{sheet.relative_to(skin).as_posix()}: {_listed(new)}")
    if len(found) > _SHEETS_SHOWN:
        rest = len(found) - _SHEETS_SHOWN
        return [*found[:_SHEETS_SHOWN], f"and {rest} more sheets"]
    return found


def _sheets(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if (
            path.suffix in _SHEETS
            and ".git" not in path.relative_to(root).parts
            and path.is_file()
            and not path.is_symlink()
        ):
            yield path


def _colours(sheet: Path) -> dict[str, str]:
    """Each colour in the sheet as #rrggbbaa, with how it was first written."""
    text = _NOT_COLOURS.sub(" ", sheet.read_text(errors="replace"))
    found: dict[str, str] = {}
    for written in _COLOUR.findall(text):
        value = _value(written)
        if not value.endswith("00"):
            found.setdefault(value, written)
    return found


def _value(written: str) -> str:
    if written.startswith("#"):
        digits = written[1:].lower()
        if len(digits) < 6:
            digits = "".join(digit * 2 for digit in digits)
        return "#" + digits.ljust(8, "f")
    numbers = re.findall(r"[0-9]*\.?[0-9]+%?", written)
    if len(numbers) < 3:
        return written
    channels = [_channel(number, 255) for number in numbers[:3]]
    alpha = _channel(numbers[3], 1) if len(numbers) > 3 else 1.0
    return "#" + "".join(f"{round(c):02x}" for c in (*channels, alpha * 255))


def _channel(number: str, scale: float) -> float:
    if number.endswith("%"):
        return float(number[:-1]) * scale / 100
    return float(number)


def _listed(colours: list[str]) -> str:
    shown = ", ".join(colours[:_SHOWN])
    rest = len(colours) - _SHOWN
    return f"{shown} and {rest} more" if rest > 0 else shown
