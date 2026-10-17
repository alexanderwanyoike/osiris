"""A Theme intent proposed by a picture."""

from __future__ import annotations

import pytest
from PIL import Image

from osiris.model.colour import Colour
from osiris.themes.from_wallpaper import intent_from
from osiris.themes.intent import Harmony, Mood


def picture(
    background: str, patch: str | None = None, share: float = 0.15
) -> Image.Image:
    """A flat picture, with a block of another colour covering `share` of it."""
    image = Image.new("RGB", (200, 100), background)
    if patch is not None:
        image.paste(patch, (0, 0, int(200 * share), 100))
    return image


def test_a_small_vivid_subject_beats_a_large_grey_ground() -> None:
    intent = intent_from(picture("#7f8082", patch="#d62828"))
    assert intent.seed.oklch[2] == pytest.approx(Colour("#d62828").oklch[2], abs=8.0)


def test_a_speck_is_not_taken_for_the_subject() -> None:
    intent = intent_from(picture("#2a6f97", patch="#ff00ff", share=0.005))
    assert intent.seed.oklch[2] == pytest.approx(Colour("#2a6f97").oklch[2], abs=8.0)


def test_a_dark_picture_proposes_a_dark_theme() -> None:
    assert intent_from(picture("#14161c", patch="#3a86ff")).dark is True


def test_a_bright_picture_proposes_a_light_theme() -> None:
    assert intent_from(picture("#f1efe9", patch="#3a86ff")).dark is False


def test_a_washed_out_picture_proposes_a_muted_theme() -> None:
    assert intent_from(picture("#8a8f94", patch="#9a8f86")).mood is Mood.MUTED


def test_a_saturated_picture_proposes_a_vivid_theme() -> None:
    assert (
        intent_from(picture("#0077b6", patch="#ff006e", share=0.5)).mood is Mood.VIVID
    )


def test_choices_made_by_the_person_win() -> None:
    intent = intent_from(
        picture("#14161c", patch="#3a86ff"),
        harmony=Harmony.TRIADIC,
        mood=Mood.PASTEL,
        dark=False,
    )
    assert (intent.harmony, intent.mood, intent.dark) == (
        Harmony.TRIADIC,
        Mood.PASTEL,
        False,
    )


def test_a_picture_with_no_colour_still_proposes_a_theme() -> None:
    intent = intent_from(picture("#808080"))
    assert intent.mood is Mood.MUTED
