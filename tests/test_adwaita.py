"""The Theme's palette as libadwaita's colours, so every libadwaita app on the
desktop, Programs included, follows the Theme."""

from __future__ import annotations

import re

from osiris.themes.adwaita import adwaita_css

PALETTE = {
    "background": "#191724",
    "surface": "#1f1d2e",
    "surfaceMuted": "#26233a",
    "border": "#403d52",
    "borderActive": "#524f67",
    "foreground": "#e0def4",
    "foregroundMuted": "#908caa",
    "accent": "#c4a7e7",
    "accentMuted": "#6e6a86",
    "success": "#9ccfd8",
    "warning": "#f6c177",
    "danger": "#eb6f92",
}


def named(css: str) -> dict[str, str]:
    return dict(re.findall(r"@define-color (\w+) (#[0-9a-f]{6});", css))


def variables(css: str) -> dict[str, str]:
    return dict(re.findall(r"--([\w-]+): (#[0-9a-f]{6});", css))


def test_windows_views_and_cards_take_the_palettes_surfaces() -> None:
    colours = named(adwaita_css({"colors": PALETTE}))
    assert colours["window_bg_color"] == "#1f1d2e"
    assert colours["window_fg_color"] == "#e0def4"
    assert colours["view_bg_color"] == "#191724"
    assert colours["headerbar_bg_color"] == "#1f1d2e"
    assert colours["card_bg_color"] == "#26233a"
    assert colours["popover_bg_color"] == "#1f1d2e"
    assert colours["dialog_bg_color"] == "#1f1d2e"


def test_the_accent_and_the_states_take_the_palettes_colours() -> None:
    colours = named(adwaita_css({"colors": PALETTE}))
    assert colours["accent_bg_color"] == "#c4a7e7"
    assert colours["destructive_bg_color"] == "#eb6f92"
    assert colours["success_bg_color"] == "#9ccfd8"
    assert colours["warning_bg_color"] == "#f6c177"
    assert colours["error_bg_color"] == "#eb6f92"


def test_text_on_the_accent_is_whichever_end_of_the_palette_reads() -> None:
    light_accent = named(adwaita_css({"colors": PALETTE}))
    dark_accent = named(adwaita_css({"colors": {**PALETTE, "accent": "#31748f"}}))
    assert light_accent["accent_fg_color"] == "#191724"
    assert dark_accent["accent_fg_color"] == "#e0def4"


def test_every_colour_is_also_given_as_a_css_variable() -> None:
    css = adwaita_css({"colors": PALETTE})
    assert {k.replace("_", "-"): v for k, v in named(css).items()} == variables(css)
