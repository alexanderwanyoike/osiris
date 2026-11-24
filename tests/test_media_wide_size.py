"""Choosing a wide picture size each image model says it allows."""

from __future__ import annotations

import pytest

from osiris.harness.media.wide_size import FULL_HD, wide_size

PRESETS = ["square_hd", "landscape_4_3", "landscape_16_9"]
CUSTOM = {"$ref": "#/components/schemas/ImageSize"}


@pytest.mark.parametrize("about", ["", "The size of the generated image."])
def test_a_model_with_no_stated_limits_gets_full_hd(about: str) -> None:
    field = {"anyOf": [CUSTOM, {"enum": PRESETS}], "description": about}

    assert wide_size(field) == FULL_HD


@pytest.mark.parametrize(
    "about",
    [
        "Concrete sizes must have both dimensions as multiples of 16.",
        "Explicit dimensions must match a supported size.",
        "Width and height must be between 1920 and 4096.",
    ],
)
def test_a_model_with_size_rules_gets_its_own_wide_preset(about: str) -> None:
    field = {"anyOf": [CUSTOM, {"enum": PRESETS}], "description": about}

    assert wide_size(field) == "landscape_16_9"


def test_a_model_listing_only_exact_sizes_gets_the_widest() -> None:
    field = {"enum": ["1024x1024", "1536x1024", "1024x1536"]}

    assert wide_size(field) == "1536x1024"


@pytest.mark.parametrize(
    "field",
    [
        {},
        {"enum": ["square", "auto"]},
        {"anyOf": [CUSTOM], "description": "Sizes must be multiples of 64."},
    ],
)
def test_a_model_with_no_wide_size_is_left_to_its_own_default(
    field: dict[str, object],
) -> None:
    assert wide_size(field) is None
