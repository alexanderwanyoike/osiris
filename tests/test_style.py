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
