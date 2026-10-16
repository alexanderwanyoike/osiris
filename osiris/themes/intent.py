"""Harmonious themes from a Theme intent.

A person or a model says what a theme should be - a seed colour, a harmony,
light or dark, a mood - and these rules decide its colours (see CONTEXT.md).
Nobody else writes colours, so every theme made this way is harmonious and
legible by construction, and reproducible from its intent.

The rules work in OKLCH, where equal steps look equal. Harmony is a turn of the
hue wheel; mood is a band of lightness and chroma; the variant fixes how light
the background is. The seed contributes only its hue: how colourful the theme
is belongs to the mood, not to whichever swatch happened to be picked.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from osiris.model.colour import Colour
from osiris.themes.derive import Seeds


class Harmony(Enum):
    ANALOGOUS = "analogous"
    COMPLEMENTARY = "complementary"
    SPLIT_COMPLEMENTARY = "split-complementary"
    TRIADIC = "triadic"
    MONOCHROME = "monochrome"


class Mood(Enum):
    MUTED = "muted"
    BALANCED = "balanced"
    VIVID = "vivid"
    PASTEL = "pastel"


@dataclass(frozen=True)
class ThemeIntent:
    seed: Colour
    harmony: Harmony = Harmony.ANALOGOUS
    mood: Mood = Mood.BALANCED
    dark: bool = True


#: Where each harmony puts its partners on the hue wheel, in degrees from the
#: seed. The first partner becomes the theme's secondary colour.
HUE_TURNS: dict[Harmony, tuple[float, ...]] = {
    Harmony.ANALOGOUS: (30.0, -30.0),
    Harmony.COMPLEMENTARY: (180.0,),
    Harmony.SPLIT_COMPLEMENTARY: (150.0, -150.0),
    Harmony.TRIADIC: (120.0, -120.0),
    Harmony.MONOCHROME: (0.0,),
}


@dataclass(frozen=True)
class _Band:
    """OKLCH lightness of the accent on dark and light backgrounds, its chroma,
    and the chroma of the background's tint."""

    on_dark: float
    on_light: float
    chroma: float
    tint: float


MOODS: dict[Mood, _Band] = {
    Mood.MUTED: _Band(on_dark=0.74, on_light=0.50, chroma=0.06, tint=0.012),
    Mood.BALANCED: _Band(on_dark=0.74, on_light=0.50, chroma=0.11, tint=0.020),
    Mood.VIVID: _Band(on_dark=0.72, on_light=0.50, chroma=0.17, tint=0.030),
    Mood.PASTEL: _Band(on_dark=0.84, on_light=0.54, chroma=0.08, tint=0.022),
}

#: Background lightness by variant. Dark sits off black and light off white:
#: pure black and white look harsh next to tinted colours.
BACKGROUND_LIGHTNESS = {True: 0.20, False: 0.965}

#: How far a monochrome secondary steps from the accent: towards the background
#: would sink it, so it steps the other way.
MONOCHROME_STEP = 0.12


def _accent(hue: float, band: _Band, dark: bool) -> Colour:
    return Colour.from_oklch(band.on_dark if dark else band.on_light, band.chroma, hue)


def _secondary(hue: float, harmony: Harmony, band: _Band, dark: bool) -> Colour:
    if harmony is Harmony.MONOCHROME:
        lightness = (
            band.on_dark + MONOCHROME_STEP if dark else band.on_light - MONOCHROME_STEP
        )
        return Colour.from_oklch(lightness, band.chroma * 0.7, hue)
    return _accent((hue + HUE_TURNS[harmony][0]) % 360.0, band, dark)


def seeds(intent: ThemeIntent) -> Seeds:
    """What osiris.themes.derive needs to build the theme's full palette."""
    hue = intent.seed.oklch[2]
    band = MOODS[intent.mood]
    return Seeds(
        background=Colour.from_oklch(BACKGROUND_LIGHTNESS[intent.dark], band.tint, hue),
        accent=_accent(hue, band, intent.dark),
        secondary=_secondary(hue, intent.harmony, band, intent.dark),
        dark=intent.dark,
    )


def partners(seed: Colour) -> dict[Harmony, list[Colour]]:
    """For each harmony, the colours that go with `seed`, at the seed's own
    lightness and chroma - what the creator offers as swatches."""
    lightness, chroma, hue = seed.oklch
    offered: dict[Harmony, list[Colour]] = {}
    for harmony, turns in HUE_TURNS.items():
        if harmony is Harmony.MONOCHROME:
            offered[harmony] = [
                Colour.from_oklch(lightness + step, chroma, hue)
                for step in (-MONOCHROME_STEP, MONOCHROME_STEP)
            ]
        else:
            offered[harmony] = [
                Colour.from_oklch(lightness, chroma, (hue + turn) % 360.0)
                for turn in turns
            ]
    return offered
