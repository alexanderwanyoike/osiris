"""Deriving a palette from three colours.

The properties asserted here are the ones that were previously checked by
looking at a screen.
"""

from __future__ import annotations

import json

import pytest

from osiris.model.colour import BODY_CONTRAST, INTERFACE_CONTRAST, Colour
from osiris.themes.derive import (
    Seeds,
    build,
    foreground,
    palette,
    semantic,
    terminal,
)

DARK = Colour("#15151c")
LIGHT = Colour("#f2f0ef")
ACCENT = Colour("#7c8aeb")

# Every combination, including the two that contradict themselves.
COMBINATIONS = [
    pytest.param(DARK, True, id="dark-background-dark-theme"),
    pytest.param(DARK, False, id="dark-background-light-theme"),
    pytest.param(LIGHT, True, id="light-background-dark-theme"),
    pytest.param(LIGHT, False, id="light-background-light-theme"),
    pytest.param(Colour("#2e3440"), True, id="nord"),
    pytest.param(Colour("#faf4ed"), False, id="rose-pine-dawn"),
]


class TestForeground:
    @pytest.mark.parametrize(("background", "dark"), COMBINATIONS)
    def test_text_is_always_readable(self, background: Colour, dark: bool) -> None:
        """Including when the declared variant contradicts the background.

        This is the regression. Trusting the flag produced black on near-black
        at a contrast ratio of 1.16.
        """
        assert foreground(background).readable_against(background, BODY_CONTRAST)

    def test_direction_follows_the_background_not_the_flag(self) -> None:
        """A dark background gets light text whatever the theme calls itself."""
        assert not foreground(DARK).is_dark
        assert foreground(LIGHT).is_dark

    def test_the_text_carries_a_little_of_the_backgrounds_hue(self) -> None:
        """A flat white on a green-grey background reads as clinical."""
        green_grey = Colour("#2d353b")
        assert foreground(green_grey).hls[2] > 0.0


class TestSemanticColours:
    @pytest.mark.parametrize(("background", "dark"), COMBINATIONS)
    def test_state_colours_clear_the_interface_threshold(
        self, background: Colour, dark: bool
    ) -> None:
        colours = palette(Seeds(background, ACCENT, dark=dark))
        for name in ("danger", "warning", "success"):
            assert Colour(colours[name]).readable_against(
                background, INTERFACE_CONTRAST
            ), f"{name} is unreadable on {background.hex}"

    def test_danger_stays_red_whatever_the_accent(self) -> None:
        """Hue is fixed; only saturation and lightness adapt.

        A state colour that drifts to the accent's hue stops communicating.
        """
        for accent in ("#7c8aeb", "#a7c080", "#c4a7e7", "#e0a44c"):
            danger = semantic(2.0, Colour(accent), DARK)
            hue = danger.hls[0] * 360
            assert hue < 20 or hue > 340, f"danger drifted to {hue:.0f} degrees"

    def test_a_pale_accent_does_not_wash_out_the_state_colours(self) -> None:
        """The bug this rule was written for: danger became salmon."""
        pale = Colour("#c4a7e7")
        assert semantic(2.0, pale, DARK).hls[2] > 0.3


class TestPalette:
    def test_every_colour_is_a_valid_hex_string(self) -> None:
        for value in palette(Seeds(DARK, ACCENT)).values():
            Colour(value)

    def test_the_seeds_appear_verbatim(self) -> None:
        colours = palette(Seeds(DARK, ACCENT))
        assert colours["background"] == DARK.hex
        assert colours["accent"] == ACCENT.hex

    def test_the_neutrals_step_away_from_the_background(self) -> None:
        colours = palette(Seeds(DARK, ACCENT))
        steps = [
            Colour(colours[name]).contrast(DARK)
            for name in ("surface", "surfaceMuted", "border")
        ]
        assert steps == sorted(steps), "neutrals must get progressively lighter"

    def test_a_secondary_is_included_only_when_given(self) -> None:
        assert "accentSecondary" not in palette(Seeds(DARK, ACCENT))
        with_secondary = palette(Seeds(DARK, ACCENT, secondary=Colour("#bb9af7")))
        assert with_secondary["accentSecondary"] == "#bb9af7"

    def test_muted_text_stays_legible(self) -> None:
        """It was once mixed so far into the background it vanished."""
        colours = palette(Seeds(DARK, ACCENT))
        assert Colour(colours["foregroundMuted"]).readable_against(
            DARK, INTERFACE_CONTRAST
        )


class TestTerminal:
    def test_all_sixteen_are_present(self) -> None:
        colours = terminal(Seeds(DARK, ACCENT))
        expected = {
            f"{weight}{n}" for weight in ("regular", "bright") for n in range(8)
        }
        assert set(colours) == expected

    @pytest.mark.parametrize(("background", "dark"), COMBINATIONS)
    def test_the_six_hues_are_readable_on_the_background(
        self, background: Colour, dark: bool
    ) -> None:
        colours = terminal(Seeds(background, ACCENT, dark=dark))
        for index in range(1, 7):
            name = f"regular{index}"
            assert Colour(colours[name]).readable_against(
                background, INTERFACE_CONTRAST
            ), f"{name} is unreadable"

    def test_bright_variants_are_brighter(self) -> None:
        colours = terminal(Seeds(DARK, ACCENT))
        for index in range(1, 7):
            regular = Colour(colours[f"regular{index}"])
            bright = Colour(colours[f"bright{index}"])
            assert bright.luminance > regular.luminance


class TestBuild:
    def test_the_document_carries_its_seeds_for_reopening(self) -> None:
        seeds = Seeds(DARK, ACCENT, secondary=Colour("#bb9af7"), dark=True)
        document = build("mine", "Mine", seeds)
        assert document["derived_from"] == {
            "background": DARK.hex,
            "accent": ACCENT.hex,
            "secondary": "#bb9af7",
        }

    def test_a_light_theme_names_the_light_gtk_and_icon_themes(self) -> None:
        document = build("pale", "Pale", Seeds(LIGHT, ACCENT, dark=False))
        ui = document["ui"]
        assert isinstance(ui, dict)
        assert ui["gtk"] == "adw-gtk3"
        assert ui["icons"] == "Papirus-Light"

    def test_optional_fields_appear_only_when_given(self) -> None:
        plain = build("a", "A", Seeds(DARK, ACCENT))
        assert "folder_colour" not in plain
        decorated = build(
            "b",
            "B",
            Seeds(DARK, ACCENT),
            folder_colour="indigo",
            wallpaper_style="arcs",
        )
        assert decorated["folder_colour"] == "indigo"
        assert decorated["wallpaper_style"] == "arcs"

    def test_the_document_is_json_serialisable(self) -> None:
        """It is written to disk as JSON; a stray Colour would break that."""
        json.dumps(build("mine", "Mine", Seeds(DARK, ACCENT)))
