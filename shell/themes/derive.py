"""Derive a full Osiris palette from a background colour and an accent.

    python3 shell/themes/derive.py '#2e3440' '#88c0d0' --dark --name nord-auto

**This module is a shim.** The derivation lives in `osiris.themes.derive`,
which is tested; this keeps the names the existing callers use while the rest
of the theme engine is migrated across. It will be deleted with them.

Keeping the old signatures here rather than editing every caller at once is
deliberate: the new code goes live immediately and is exercised by the running
desktop, instead of sitting in a parallel tree that nothing executes.
"""

import argparse
import json
import os
import sys

# The package is installed beside this file on a target, and lives two
# directories up in a checkout.
for candidate in (
    "/usr/share/osiris/lib",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
):
    if os.path.isdir(os.path.join(candidate, "osiris")):
        sys.path.insert(0, candidate)
        break

from osiris.model.colour import MID_LUMINANCE, Colour  # noqa: E402
from osiris.themes import derive as _derive  # noqa: E402

__all__ = [
    "MID_LUMINANCE",
    "build",
    "contrast",
    "derive",
    "luminance",
    "mix",
    "to_hex",
    "to_hls",
    "to_rgb",
]


# --------------------------------------------------------------------------- #
# the old free functions, over the Colour model


def to_rgb(value: str) -> tuple[float, float, float]:
    return Colour(value).rgb


def to_hex(rgb) -> str:
    return Colour.from_rgb(*rgb).hex


def to_hls(value: str) -> tuple[float, float, float]:
    hue, lightness, saturation = Colour(value).hls
    return hue, lightness, saturation


def mix(a: str, b: str, t: float) -> str:
    return Colour(a).mix(Colour(b), t).hex


def luminance(value: str) -> float:
    return Colour(value).luminance


def contrast(a: str, b: str) -> float:
    return Colour(a).contrast(Colour(b))


def _seeds(
    background: str, accent: str, dark: bool, secondary: str | None
) -> _derive.Seeds:
    return _derive.Seeds(
        background=Colour(background),
        accent=Colour(accent),
        secondary=Colour(secondary) if secondary else None,
        dark=dark,
    )


def derive(
    background: str, accent: str, dark: bool = True, secondary: str | None = None
) -> dict:
    seeds = _seeds(background, accent, dark, secondary)
    return {"colors": _derive.palette(seeds), "terminal": _derive.terminal(seeds)}


def build(
    name: str,
    label: str,
    background: str,
    accent: str,
    dark: bool = True,
    secondary: str | None = None,
) -> dict:
    """A complete theme document, ready to write to disk."""
    return _derive.build(name, label, _seeds(background, accent, dark, secondary))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("background")
    parser.add_argument("accent")
    parser.add_argument("--secondary")
    parser.add_argument("--name", default="custom")
    parser.add_argument("--label")
    parser.add_argument("--light", action="store_true")
    args = parser.parse_args()

    try:
        theme = build(
            args.name,
            args.label or args.name.title(),
            args.background,
            args.accent,
            dark=not args.light,
            secondary=args.secondary,
        )
    except ValueError as error:
        sys.exit(f"error: {error}")
    print(json.dumps(theme, indent=4))


if __name__ == "__main__":
    main()
