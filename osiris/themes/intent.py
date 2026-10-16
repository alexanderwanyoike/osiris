"""Harmonious themes from a Theme intent."""

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


def seeds(intent: ThemeIntent) -> Seeds:
    raise NotImplementedError


def partners(seed: Colour) -> dict[Harmony, list[Colour]]:
    raise NotImplementedError
