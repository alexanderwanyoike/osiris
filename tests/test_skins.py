"""A Skin carries shape and no colour (CONTEXT.md), so it works under any Theme."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from osiris.harness.style import SKINS, VARIABLES

SKIN_DIR = Path(__file__).resolve().parent.parent / "apps" / "harness" / "skins"

# Colour literals a stylesheet could hide in: hex, functional notation, and the
# CSS named colours most likely to slip in.
LITERALS = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch|oklab)\s*\("
    r"|\b(?:white|black|red|green|blue|gray|grey|silver|yellow|orange|purple)\b"
)
# Every class the drawer gives its widgets; each Skin has to say how they look.
CLASSES = (
    "harness-drawer",
    "harness-surface",
    "harness-header",
    "harness-question",
    "harness-answer",
    "harness-heading",
    "harness-code",
    "harness-code-header",
    "harness-quote",
    "harness-table",
    "harness-chip",
    "harness-meta",
    "harness-composer",
    "harness-provider",
    "harness-key-form",
    "harness-code-form",
    "harness-provider-card",
    "harness-monogram",
    "harness-connected",
)


def stylesheet(name: str) -> str:
    text = (SKIN_DIR / f"{name}.css").read_text()
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


@pytest.mark.parametrize("name", SKINS)
def test_every_skin_exists(name: str) -> None:
    assert (SKIN_DIR / f"{name}.css").is_file()


@pytest.mark.parametrize("name", SKINS)
def test_a_skin_names_no_colour_of_its_own(name: str) -> None:
    assert LITERALS.findall(stylesheet(name)) == []


@pytest.mark.parametrize("name", SKINS)
def test_a_skin_only_refers_to_colours_the_theme_provides(name: str) -> None:
    used = set(re.findall(r"@([a-z_]+)", stylesheet(name)))
    assert used <= set(VARIABLES), used - set(VARIABLES)


@pytest.mark.parametrize("name", SKINS)
def test_a_skin_styles_every_part_of_the_drawer(name: str) -> None:
    text = stylesheet(name)
    missing = [c for c in CLASSES if f".{c}" not in text]
    assert missing == []


@pytest.mark.parametrize("name", SKINS)
def test_the_window_itself_is_transparent_so_the_surface_can_float(name: str) -> None:
    """The drawer's shape is its surface; the window around it must not paint, or
    the rounded corners show a square behind them."""
    rule = re.search(r"window\.harness-drawer[^{]*\{([^}]*)\}", stylesheet(name))
    assert rule is not None
    assert "transparent" in rule.group(1)
