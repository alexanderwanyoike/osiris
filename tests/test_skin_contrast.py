"""A shipped Skin writes on accent and danger fills in whichever of the Theme's
light and dark text reads better, so every Theme keeps its buttons legible."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from osiris.platform.process import SubprocessRunner
from osiris.skins.build import build
from osiris.skins.pack import read

ROOT = Path(__file__).resolve().parent.parent
THEMES = ("rose-pine", "rose-pine-dawn", "osiris-obsidian", "nord")
# WCAG AA for body text.
LEGIBLE = 4.5

FILLED = (".view:selected", "button.suggested-action", "button.destructive-action")
SHEETS = {
    "graphite": FILLED,
    "orchis": FILLED,
    "qogir": FILLED,
    "jasper": FILLED,
    "colloid": FILLED,
    "elementary": ("check:checked", "button.destructive-action:not(:disabled)"),
}

Colour = tuple[float, ...]


def rgb(hex_colour: str) -> Colour:
    digits = hex_colour.lstrip("#")
    if len(digits) == 3:
        digits = "".join(d * 2 for d in digits)
    r, g, b = (int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return r, g, b


def luminance(colour: Colour) -> float:
    def linear(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(v) for v in colour)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: Colour, b: Colour) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def parse(value: str, named: dict[str, str]) -> tuple[Colour, float]:
    value = value.strip()
    if value.startswith("@"):
        return parse(named[value[1:]], named)
    if value in ("white", "black"):
        return rgb("#fff" if value == "white" else "#000"), 1.0
    if value.startswith("#"):
        return rgb(value), 1.0
    found = re.fullmatch(r"rgba\(([^)]*)\)", value)
    assert found, f"cannot read colour {value!r}"
    r, g, b, alpha = (float(n) for n in found[1].split(","))
    return (r / 255, g / 255, b / 255), alpha


def declared(css: str, selector: str) -> dict[str, str]:
    """The colours the rules naming exactly ``selector`` set, last one winning."""
    found: dict[str, str] = {}
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if selector not in (" ".join(s.split()) for s in selectors.split(",")):
            continue
        for prop, value in re.findall(r"(?:^|;)\s*([a-z-]+)\s*:\s*([^;]+)", body):
            if prop in ("color", "background-color"):
                found[prop] = value
    return found


def compiled(skin: str, theme: dict[str, object], tmp_path: Path) -> str:
    built = build(
        read(ROOT / "shell" / "skins" / skin),
        theme,
        tmp_path / "themes",
        tmp_path / "work",
        SubprocessRunner(),
        only=("gtk-3.0",),
    )
    return (tmp_path / "themes" / built.theme / "gtk-3.0" / "gtk.css").read_text()


@pytest.mark.skipif(shutil.which("sassc") is None, reason="needs sassc")
@pytest.mark.parametrize("theme_name", THEMES)
@pytest.mark.parametrize("skin", SHEETS)
def test_text_on_a_fill_is_the_themes_more_legible_ink(
    skin: str, theme_name: str, tmp_path: Path
) -> None:
    theme = json.loads((ROOT / "shell" / "themes" / f"{theme_name}.json").read_text())
    inks = (rgb(theme["colors"]["foreground"]), rgb(theme["colors"]["background"]))
    css = re.sub(r"/\*.*?\*/", "", compiled(skin, theme, tmp_path), flags=re.S)
    named = dict(re.findall(r"@define-color\s+(\w+)\s+([^;]+);", css))
    for selector in SHEETS[skin]:
        colours = declared(css, selector)
        fill, opacity = parse(colours["background-color"], named)
        assert opacity == 1, selector
        text, alpha = parse(colours["color"], named)
        seen = tuple(
            t * alpha + f * (1 - alpha) for t, f in zip(text, fill, strict=True)
        )
        best = max(contrast(ink, fill) for ink in inks)
        assert contrast(seen, fill) >= min(LEGIBLE, best), selector


@pytest.mark.skipif(shutil.which("sassc") is None, reason="needs sassc")
def test_qogir_draws_links_in_the_themes_accent(tmp_path: Path) -> None:
    theme = json.loads((ROOT / "shell" / "themes" / "rose-pine.json").read_text())
    css = compiled("qogir", theme, tmp_path)
    assert declared(css, "*:link")["color"] == theme["colors"]["accent"]
