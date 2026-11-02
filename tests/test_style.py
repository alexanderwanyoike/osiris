"""The drawer's colours and code highlighting, generated from a Theme's palette."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from osiris.harness.markdown import InlineStyle
from osiris.harness.style import (
    DEFAULT_SKIN,
    SCHEME_ID,
    SKINS,
    VARIABLES,
    colours_css,
    inline_style,
    skin_name,
    source_scheme,
)
from osiris.model.colour import Colour

THEMES = Path(__file__).resolve().parent.parent / "shell" / "themes"


def theme(name: str) -> dict[str, object]:
    loaded: dict[str, object] = json.loads((THEMES / f"{name}.json").read_text())
    return loaded


OBSIDIAN = theme("osiris-obsidian")
DAWN = theme("rose-pine-dawn")


def defined(css: str) -> dict[str, str]:
    return dict(re.findall(r"@define-color (\S+) (#[0-9a-fA-F]{6});", css))


def styles(xml: str) -> dict[str, dict[str, str]]:
    root = ET.fromstring(xml)
    return {node.attrib["name"]: node.attrib for node in root.iter("style")}


class TestColours:
    def test_every_variable_a_skin_may_use_is_defined(self) -> None:
        assert set(VARIABLES) <= set(defined(colours_css(OBSIDIAN)))

    def test_the_drawer_takes_the_palettes_surfaces_and_text(self) -> None:
        colours = defined(colours_css(OBSIDIAN))
        assert colours["harness_bg"] == "#1a1a1f"
        assert colours["harness_fg"] == "#e8e8e8"
        assert colours["harness_accent"] == "#7c8aeb"
        assert colours["harness_sunken"] == "#0d0d10"

    def test_libadwaita_widgets_in_the_drawer_match_the_palette(self) -> None:
        colours = defined(colours_css(OBSIDIAN))
        assert colours["window_bg_color"] == "#1a1a1f"
        assert colours["accent_bg_color"] == "#7c8aeb"

    def test_the_sidebar_in_the_drawer_matches_the_palette(self) -> None:
        colours = defined(colours_css(OBSIDIAN))
        assert colours["sidebar_bg_color"] == colours["harness_raised"]
        assert colours["sidebar_fg_color"] == colours["harness_fg"]

    @pytest.mark.parametrize("palette", [OBSIDIAN, DAWN])
    def test_glass_is_the_sidebars_surface_frosted_in_the_themes_own_colour(
        self, palette: dict[str, object]
    ) -> None:
        from osiris.model.colour import Colour, hue_distance

        colours = defined(colours_css(palette))
        raised, glass = (
            Colour(colours["harness_raised"]),
            Colour(colours["harness_glass"]),
        )
        accent, edge = (
            Colour(colours["harness_accent"]),
            Colour(colours["harness_glass_edge"]),
        )
        assert glass != raised
        assert hue_distance(glass, accent) < hue_distance(raised, accent)
        assert edge.contrast(raised) > glass.contrast(raised)

    @pytest.mark.parametrize("palette", [OBSIDIAN, DAWN])
    def test_text_on_the_accent_is_whichever_end_of_the_palette_reads(
        self, palette: dict[str, object]
    ) -> None:
        colours = defined(colours_css(palette))
        on_accent = colours["harness_on_accent"]
        palette_colours = palette["colors"]
        assert isinstance(palette_colours, dict)
        assert on_accent in (
            palette_colours["background"],
            palette_colours["foreground"],
        )


class TestScheme:
    def test_it_is_one_scheme_id_whatever_the_theme(self) -> None:
        for palette in (OBSIDIAN, DAWN):
            root = ET.fromstring(source_scheme(palette))
            assert root.tag == "style-scheme"
            assert root.attrib["id"] == SCHEME_ID
            assert root.attrib["version"] == "1.0"

    def test_code_sits_on_the_palettes_sunken_background(self) -> None:
        text = styles(source_scheme(OBSIDIAN))["text"]
        assert text["background"] == "#0d0d10"
        assert text["foreground"] == "#e8e8e8"

    def test_syntax_takes_the_terminal_colours_so_code_matches_ghostty(self) -> None:
        terminal = OBSIDIAN["terminal"]
        assert isinstance(terminal, dict)
        found = styles(source_scheme(OBSIDIAN))
        assert found["def:string"]["foreground"] == terminal["regular2"]
        assert found["def:keyword"]["foreground"] == terminal["regular5"]
        assert found["def:function"]["foreground"] == terminal["regular4"]
        assert found["def:type"]["foreground"] == terminal["regular6"]
        assert found["def:number"]["foreground"] == terminal["regular3"]

    def test_comments_are_muted_and_italic(self) -> None:
        comment = styles(source_scheme(OBSIDIAN))["def:comment"]
        assert comment["foreground"] == "#a0a0a8"
        assert comment["italic"] == "true"

    def test_a_diffs_added_and_removed_lines_take_success_and_danger(self) -> None:
        """GtkSourceView's diff language names its own styles and maps them
        to no def: style, so a scheme without them draws a diff plain."""
        found = styles(source_scheme(OBSIDIAN))
        colours = OBSIDIAN["colors"]
        assert isinstance(colours, dict)
        assert found["diff:added-line"]["foreground"] == colours["success"]
        assert found["diff:removed-line"]["foreground"] == colours["danger"]

    def test_line_numbers_sit_quieter_than_muted_text(self) -> None:
        """Between the muted text and the background, so the code leads."""
        numbers = styles(source_scheme(OBSIDIAN))["line-numbers"]["foreground"]
        colours = OBSIDIAN["colors"]
        assert isinstance(colours, dict)

        def level(hex_colour: str) -> int:
            return sum(int(hex_colour[i : i + 2], 16) for i in (1, 3, 5))

        assert level(colours["background"]) < level(numbers)
        assert level(numbers) < level(colours["foregroundMuted"])


class TestCodeFont:
    def test_code_is_set_in_the_themes_terminal_font_with_its_ligatures(self) -> None:
        """The font ghostty uses, so code reads the same in both."""
        from osiris.harness.style import code_font_css

        css = code_font_css(OBSIDIAN)
        assert 'font-family: "FiraCode Nerd Font"' in css
        assert 'font-feature-settings: "calt", "liga"' in css

    def test_a_theme_naming_no_terminal_font_falls_back_to_monospace(self) -> None:
        from osiris.harness.style import code_font_css

        plain = {key: value for key, value in OBSIDIAN.items() if key != "ui"}
        assert 'font-family: "monospace"' in code_font_css(plain)


class TestInline:
    def test_inline_code_uses_the_raised_surface(self) -> None:
        assert inline_style(OBSIDIAN) == InlineStyle(
            code_foreground="#e8e8e8", code_background="#2a2a2f"
        )


class TestSkinChoice:
    def test_there_are_at_least_two_skins_and_a_default_among_them(self) -> None:
        assert len(SKINS) >= 2
        assert DEFAULT_SKIN in SKINS

    @pytest.mark.parametrize("text", [None, "", "  ", "nonsense", "../etc/passwd"])
    def test_anything_unknown_falls_back_to_the_default(self, text: str | None) -> None:
        assert skin_name(text) == DEFAULT_SKIN

    def test_a_known_skin_is_chosen_ignoring_surrounding_whitespace(self) -> None:
        assert skin_name(" transcript\n") == "transcript"

    def test_studio_can_be_chosen(self) -> None:
        assert skin_name("studio") == "studio"

    def test_studio_is_the_look_when_none_is_chosen(self) -> None:
        assert skin_name(None) == "studio"


class TestTokens:
    def test_a_picked_token_is_the_accent_on_a_wash_of_it(self) -> None:
        from osiris.harness.style import token_colours

        assert token_colours(OBSIDIAN) == ("#7c8aeb", "#2e3048")


class TestContextRing:
    def test_the_ring_is_a_more_vivid_accent_turning_to_danger(self) -> None:
        from osiris.harness.style import ring_colours

        colours = OBSIDIAN["colors"]
        ring = ring_colours(OBSIDIAN)
        accent = Colour(colours["accent"]).oklch
        danger = Colour(colours["danger"]).oklch
        calm, full = Colour(ring.at(0.0)).oklch, Colour(ring.at(1.0)).oklch
        assert abs(calm[2] - accent[2]) < 2 and calm[1] > accent[1]
        assert abs(full[2] - danger[2]) < 2 and full[1] > danger[1]

    def test_the_ring_stays_vivid_on_its_way_to_danger(self) -> None:
        from osiris.harness.style import ring_colours

        colours = OBSIDIAN["colors"]
        least = min(Colour(colours[k]).oklch[1] for k in ("accent", "danger"))
        ring = ring_colours(OBSIDIAN)
        assert all(Colour(ring.at(a)).oklch[1] >= least for a in (0.25, 0.5, 0.75))

    def test_the_rings_track_is_a_faint_line_on_the_card(self) -> None:
        from osiris.harness.style import ring_colours

        colours = OBSIDIAN["colors"]
        track = ring_colours(OBSIDIAN).track
        assert track not in (colours["surfaceMuted"].lower(), colours["foreground"])
