"""A full palette from two or three colours.

A theme needs about thirty colours; the creator asks for three. This fills in
the rest, and the result is written into the saved theme rather than recomputed
on load, so a theme is a document that can be hand-edited and does not shift
under the user when this file improves.

Three groups, derived differently:

* **Neutrals** - surfaces, borders, muted text - are the background stepped
  towards the foreground. Interpolation, no decisions.
* **State colours** must stay recognisably green, amber and red or they stop
  meaning anything, so their hue is fixed and only saturation and lightness are
  matched to the palette.
* **Terminal colours** likewise keep their hue: a shell printing red has to
  look red.
"""

from __future__ import annotations

from dataclasses import dataclass

from osiris.model.colour import (
    BLACK,
    BODY_CONTRAST,
    INTERFACE_CONTRAST,
    WHITE,
    Colour,
)

#: Hues that carry meaning, in degrees. Only saturation and lightness adapt;
#: moving these would break what they communicate.
SEMANTIC_HUES = {"danger": 2.0, "warning": 40.0, "success": 130.0}
ANSI_HUES = {
    "red": 2.0,
    "green": 130.0,
    "yellow": 40.0,
    "blue": 215.0,
    "magenta": 290.0,
    "cyan": 185.0,
}
ANSI_ORDER = ("red", "green", "yellow", "blue", "magenta", "cyan")


@dataclass(frozen=True)
class Seeds:
    """What the creator asks a human for."""

    background: Colour
    accent: Colour
    secondary: Colour | None = None
    dark: bool = True


def foreground(background: Colour) -> Colour:
    """Readable text, tinted towards the background's hue.

    A flat white on a green-grey background looks clinical and out of family;
    carrying a little of the background's hue keeps it coherent. The tint is
    backed off until the contrast ratio clears the AAA body-text threshold.

    Which direction to go is decided by **measuring the background**, not by
    the theme's declared light/dark flag. Those two can disagree - the creator
    lets the variant be flipped before a matching background is chosen - and
    when they did, this returned black text on a near-black ground at a
    contrast ratio of 1.16. Legibility is not a preference to be honoured.
    """
    hue, _, saturation = background.hls
    tint = min(saturation, 0.18)
    lighten = background.is_dark
    lightness = 0.93 if lighten else 0.16
    step = 0.01 if lighten else -0.01

    for _ in range(12):
        candidate = Colour.from_hls(hue, lightness, tint)
        if candidate.readable_against(background, BODY_CONTRAST):
            return candidate
        lightness += step
    return WHITE if lighten else BLACK


def semantic(hue_degrees: float, accent: Colour, background: Colour) -> Colour:
    """A meaning-carrying colour, fitted to the palette's depth.

    Saturation deliberately does not follow the accent. A pale accent dragged
    "danger" to a washed-out salmon that no longer read as an error, so these
    sit in a narrow band measured against the hand-tuned palettes, with only a
    light pull towards the accent so they do not look pasted on.
    """
    _, _, accent_saturation = accent.hls
    saturation = 0.42 + (min(accent_saturation, 0.8) - 0.5) * 0.30
    lighten = background.is_dark
    lightness = 0.64 if lighten else 0.44
    step = 0.03 if lighten else -0.03

    candidate = Colour.from_hls(hue_degrees / 360.0, lightness, saturation)
    for _ in range(14):
        if candidate.readable_against(background, INTERFACE_CONTRAST):
            return candidate
        lightness += step
        candidate = Colour.from_hls(hue_degrees / 360.0, lightness, saturation)
    return candidate


def palette(seeds: Seeds) -> dict[str, str]:
    """The thirty-odd interface colours."""
    background, accent = seeds.background, seeds.accent
    text = foreground(background)

    colours = {
        "background": background,
        # Neutrals: the background stepped towards the text colour. Small even
        # steps keep the surfaces distinguishable without banding.
        "surface": background.mix(text, 0.06),
        "surfaceMuted": background.mix(text, 0.13),
        "border": background.mix(text, 0.20),
        "borderActive": accent,
        "foreground": text,
        # 0.42 looked right in isolation but produced muted text far darker
        # than any hand-tuned palette; measured against those, 0.26 matches.
        "foregroundMuted": text.mix(background, 0.26),
        "accent": accent,
        "accentMuted": accent.mix(background, 0.45),
    }
    for name, degrees in SEMANTIC_HUES.items():
        colours[name] = semantic(degrees, accent, background)
    if seeds.secondary is not None:
        colours["accentSecondary"] = seeds.secondary
    return {name: colour.hex for name, colour in colours.items()}


def terminal(seeds: Seeds) -> dict[str, str]:
    """The sixteen ANSI colours, fitted the same way as the state colours."""
    background, accent = seeds.background, seeds.accent
    text = foreground(background)
    lighten = background.is_dark

    normals = {
        name: semantic(degrees, accent, background)
        for name, degrees in ANSI_HUES.items()
    }
    colours: dict[str, Colour] = {
        "regular0": background.mix(text, 0.13),
        "regular7": text,
        "bright0": background.mix(text, 0.20),
        "bright7": text.mix(WHITE, 0.5 if lighten else 0.0),
    }
    toward = WHITE if lighten else BLACK
    for index, name in enumerate(ANSI_ORDER, start=1):
        colours[f"regular{index}"] = normals[name]
        colours[f"bright{index}"] = normals[name].mix(toward, 0.22)

    return {
        name: colours[name].hex
        for name in sorted(colours, key=lambda s: (s.startswith("bright"), s))
    }
