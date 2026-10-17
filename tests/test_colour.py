"""Colour arithmetic, and the legibility rules that depend on it."""

from __future__ import annotations

import pytest

from osiris.model.colour import (
    BLACK,
    BODY_CONTRAST,
    WHITE,
    Colour,
    InvalidColour,
    hue_distance,
)


class TestParsing:
    def test_a_six_digit_hex_colour_is_accepted(self) -> None:
        assert Colour("#7C8AEB").hex == "#7c8aeb"

    @pytest.mark.parametrize("bad", ["7c8aeb", "#7c8ae", "#gggggg", "", "#7c8aebff"])
    def test_anything_else_is_refused(self, bad: str) -> None:
        with pytest.raises(InvalidColour):
            Colour(bad)

    def test_round_trips_through_rgb(self) -> None:
        colour = Colour("#7c8aeb")
        assert Colour.from_rgb(*colour.rgb) == colour

    def test_round_trips_through_hls(self) -> None:
        colour = Colour("#a7c080")
        hue, lightness, saturation = colour.hls
        assert Colour.from_hls(hue, lightness, saturation) == colour


class TestContrast:
    def test_black_on_white_is_the_maximum(self) -> None:
        assert BLACK.contrast(WHITE) == pytest.approx(21.0, abs=0.01)

    def test_a_colour_against_itself_is_the_minimum(self) -> None:
        assert Colour("#7c8aeb").contrast(Colour("#7c8aeb")) == pytest.approx(1.0)

    def test_contrast_is_symmetric(self) -> None:
        one, other = Colour("#15151c"), Colour("#ebebf0")
        assert one.contrast(other) == pytest.approx(other.contrast(one))

    def test_the_bug_this_module_exists_for(self) -> None:
        """Black text on a near-black ground.

        A "light" theme whose background had not yet been changed derived this
        pair, and shipped. 1.16 is unreadable; the assertion is the point.
        """
        background = Colour("#15151c")
        assert BLACK.contrast(background) < 1.2
        assert not BLACK.readable_against(background)

    def test_the_colour_that_should_have_been_chosen_is_readable(self) -> None:
        background = Colour("#15151c")
        assert Colour("#ebebf0").readable_against(background)
        assert Colour("#ebebf0").contrast(background) > BODY_CONTRAST


class TestDarkness:
    @pytest.mark.parametrize("value", ["#000000", "#15151c", "#2e3440", "#4f4f4f"])
    def test_dark_backgrounds_are_recognised(self, value: str) -> None:
        assert Colour(value).is_dark

    @pytest.mark.parametrize("value", ["#ffffff", "#faf4ed", "#f2f0ef", "#e4e4e4"])
    def test_light_backgrounds_are_recognised(self, value: str) -> None:
        assert not Colour(value).is_dark


class TestMixing:
    def test_mixing_none_returns_the_original(self) -> None:
        assert Colour("#7c8aeb").mix(WHITE, 0.0) == Colour("#7c8aeb")

    def test_mixing_all_returns_the_other(self) -> None:
        assert Colour("#7c8aeb").mix(WHITE, 1.0) == WHITE

    def test_mixing_half_lands_between(self) -> None:
        middle = BLACK.mix(WHITE, 0.5)
        assert middle.luminance > BLACK.luminance
        assert middle.luminance < WHITE.luminance


class TestHueDistance:
    def test_a_colour_is_no_distance_from_itself(self) -> None:
        assert hue_distance(Colour("#e25252"), Colour("#e25252")) == 0.0

    def test_the_hue_circle_wraps(self) -> None:
        """Red sits either side of zero; the short way round is the answer."""
        just_below = Colour.from_hls(0.99, 0.5, 0.8)
        just_above = Colour.from_hls(0.01, 0.5, 0.8)
        assert hue_distance(just_below, just_above) < 0.05

    def test_opposites_are_at_the_maximum(self) -> None:
        """Tolerance is for 8-bit quantisation, not slack.

        A colour round-tripped through sRGB bytes comes back with a hue a
        thousandth or so off where it went in.
        """
        distance = hue_distance(
            Colour.from_hls(0.0, 0.5, 0.8), Colour.from_hls(0.5, 0.5, 0.8)
        )
        assert distance == pytest.approx(0.5, abs=0.005)


class TestOklch:
    """OKLCH, from Björn Ottosson's OKLab, against its published values."""

    @pytest.mark.parametrize(
        ("hex_", "lightness", "chroma", "hue"),
        [
            ("#ff0000", 0.6280, 0.2577, 29.23),
            ("#00ff00", 0.8664, 0.2948, 142.50),
            ("#0000ff", 0.4520, 0.3132, 264.05),
        ],
    )
    def test_primaries_match_the_reference(
        self, hex_: str, lightness: float, chroma: float, hue: float
    ) -> None:
        got = Colour(hex_).oklch
        assert got[0] == pytest.approx(lightness, abs=1e-3)
        assert got[1] == pytest.approx(chroma, abs=1e-3)
        assert got[2] == pytest.approx(hue, abs=0.1)

    def test_white_is_full_lightness_and_no_chroma(self) -> None:
        lightness, chroma, _ = WHITE.oklch
        assert lightness == pytest.approx(1.0, abs=1e-3)
        assert chroma == pytest.approx(0.0, abs=1e-3)

    def test_black_is_zero_lightness(self) -> None:
        assert BLACK.oklch[0] == pytest.approx(0.0, abs=1e-6)

    @pytest.mark.parametrize("hex_", ["#7c8aeb", "#2e3440", "#a7c080", "#eb6f92"])
    def test_round_trips(self, hex_: str) -> None:
        assert Colour.from_oklch(*Colour(hex_).oklch) == Colour(hex_)

    def test_an_unreachable_colour_keeps_its_lightness_and_hue(self) -> None:
        colour = Colour.from_oklch(0.7, 0.4, 150.0)
        lightness, chroma, hue = colour.oklch
        assert lightness == pytest.approx(0.7, abs=0.02)
        assert hue == pytest.approx(150.0, abs=2.0)
        assert chroma < 0.4
