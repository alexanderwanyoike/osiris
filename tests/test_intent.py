"""Harmonious themes from a Theme intent.

A model, or a person, says what a theme should be; these rules decide its
colours. So the properties asserted here are promises: harmony in the hues,
the variant in the background, and legibility across every combination.
"""

from __future__ import annotations

import itertools

import pytest

from osiris.model.colour import Colour
from osiris.themes.derive import palette
from osiris.themes.intent import (
    Harmony,
    Mood,
    ThemeIntent,
    harmonise,
    partners,
    seeds,
    suggestions,
)

TEAL = Colour("#2aa198")


def hue(colour: Colour) -> float:
    return colour.oklch[2]


def hue_gap(one: Colour, other: Colour) -> float:
    return (hue(other) - hue(one)) % 360.0


@pytest.mark.parametrize(
    ("harmony", "offset"),
    [
        (Harmony.ANALOGOUS, 30.0),
        (Harmony.COMPLEMENTARY, 180.0),
        (Harmony.SPLIT_COMPLEMENTARY, 150.0),
        (Harmony.TRIADIC, 120.0),
    ],
)
def test_the_secondary_sits_at_its_harmony(harmony: Harmony, offset: float) -> None:
    result = seeds(ThemeIntent(seed=TEAL, harmony=harmony))
    assert result.secondary is not None
    assert hue_gap(result.accent, result.secondary) == pytest.approx(offset, abs=4.0)


@pytest.mark.parametrize("harmony", [h for h in Harmony if h is not Harmony.MONOCHROME])
@pytest.mark.parametrize("mood", list(Mood))
def test_the_secondary_supports_rather_than_competes(
    harmony: Harmony, mood: Mood
) -> None:
    """One strong colour and a quieter partner: two at equal strength fight."""
    result = seeds(ThemeIntent(seed=TEAL, harmony=harmony, mood=mood))
    assert result.secondary is not None
    assert result.secondary.oklch[1] < result.accent.oklch[1] * 0.85


def test_a_monochrome_secondary_keeps_the_hue_and_moves_lightness() -> None:
    result = seeds(ThemeIntent(seed=TEAL, harmony=Harmony.MONOCHROME))
    assert result.secondary is not None
    assert hue(result.secondary) == pytest.approx(hue(result.accent), abs=4.0)
    assert abs(result.secondary.oklch[0] - result.accent.oklch[0]) > 0.1


def test_the_accent_carries_the_seeds_hue() -> None:
    assert hue(seeds(ThemeIntent(seed=TEAL)).accent) == pytest.approx(
        hue(TEAL), abs=4.0
    )


@pytest.mark.parametrize("dark", [True, False])
def test_the_background_follows_the_variant(dark: bool) -> None:
    result = seeds(ThemeIntent(seed=TEAL, dark=dark))
    assert result.background.is_dark is dark
    assert result.dark is dark


def test_the_background_is_tinted_with_the_seeds_hue() -> None:
    background = seeds(ThemeIntent(seed=TEAL)).background
    assert hue(background) == pytest.approx(hue(TEAL), abs=12.0)


def test_vivid_is_more_colourful_than_muted() -> None:
    def chroma(mood: Mood) -> float:
        return seeds(ThemeIntent(seed=TEAL, mood=mood)).accent.oklch[1]

    assert chroma(Mood.VIVID) > chroma(Mood.BALANCED) > chroma(Mood.MUTED)


def test_pastel_is_lighter_than_vivid_on_a_dark_theme() -> None:
    def lightness(mood: Mood) -> float:
        return seeds(ThemeIntent(seed=TEAL, mood=mood)).accent.oklch[0]

    assert lightness(Mood.PASTEL) > lightness(Mood.VIVID)


HUES = [Colour.from_oklch(0.65, 0.12, float(h)) for h in range(0, 360, 30)]


@pytest.mark.parametrize(
    ("seed", "harmony", "mood", "dark"),
    list(itertools.product(HUES, Harmony, Mood, [True, False])),
)
def test_every_combination_is_legible(
    seed: Colour, harmony: Harmony, mood: Mood, dark: bool
) -> None:
    result = seeds(ThemeIntent(seed=seed, harmony=harmony, mood=mood, dark=dark))
    colours = {k: Colour(v) for k, v in palette(result).items()}
    background = colours["background"]
    assert colours["foreground"].contrast(background) >= 7.0
    assert colours["accent"].contrast(background) >= 3.0
    assert colours["accentSecondary"].contrast(background) >= 3.0


def test_partners_offer_every_harmony_for_a_colour() -> None:
    offered = partners(TEAL)
    assert set(offered) == set(Harmony)
    assert all(colours for colours in offered.values())


def test_suggestions_are_distinct_named_starting_points() -> None:
    offered = suggestions(TEAL, dark=True)
    names = [name for name, _ in offered]
    assert len(names) == len(set(names)) == 6
    combos = {(i.harmony, i.mood) for _, i in offered}
    assert len(combos) == 6


def test_suggestions_share_the_seed_and_the_variant() -> None:
    for _, intent in suggestions(TEAL, dark=False):
        assert intent.seed == TEAL
        assert intent.dark is False


HARMONY_TURNS = [0.0, 30.0, 120.0, 150.0, 180.0, 210.0, 240.0, 330.0]


@pytest.mark.parametrize(
    "hex_", ["#e4572e", "#29335c", "#f3a712", "#a8c686", "#669bbc"]
)
def test_harmonising_snaps_a_secondary_to_a_harmony(hex_: str) -> None:
    accent = Colour("#7aa2f7")
    fixed = harmonise(accent, Colour(hex_))
    turn = hue_gap(accent, fixed)
    assert min(abs(turn - t) for t in HARMONY_TURNS) < 3.0


def test_harmonising_makes_the_secondary_support_the_accent() -> None:
    accent = Colour("#7aa2f7")
    fixed = harmonise(accent, Colour("#e4572e"))
    assert fixed.oklch[1] < accent.oklch[1] * 0.85


def test_harmonising_twice_changes_nothing_more() -> None:
    accent = Colour("#7aa2f7")
    once = harmonise(accent, Colour("#e4572e"))
    assert harmonise(accent, once) == once
