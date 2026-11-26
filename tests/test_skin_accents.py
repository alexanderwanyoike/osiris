"""Jasper and Graphite mark a selected file in the Theme's accent, and Graphite
keeps Files' sidebar plain, as the other shipped Skins do."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from tests.test_skin_contrast import LEGIBLE, compiled, contrast, declared, parse, rgb

ROOT = Path(__file__).resolve().parent.parent
THEME = json.loads((ROOT / "shell" / "themes" / "osiris-obsidian.json").read_text())
ACCENT = rgb(THEME["colors"]["accent"])


def fill(css: str, selector: str) -> tuple[tuple[float, ...], float]:
    named = dict(re.findall(r"@define-color\s+(\w+)\s+([^;]+);", css))
    return parse(declared(css, selector)["background-color"], named)


def colour(css: str, selector: str) -> tuple[float, ...]:
    return fill(css, selector)[0]


@pytest.mark.skipif(shutil.which("sassc") is None, reason="needs sassc")
@pytest.mark.parametrize(
    "selector",
    [
        ".csd treeview.view:selected",
        ".background.csd .view:selected",
        # Files' window is decorated by the window manager, not GTK, so its
        # list takes the plain rule; found by hand on the VM.
        "treeview.view:selected",
    ],
)
def test_jasper_fills_a_selected_file_with_the_accent(
    selector: str, tmp_path: Path
) -> None:
    """Upstream marks a selected file or row with a grey wash."""
    css = compiled("jasper", THEME, tmp_path)
    assert colour(css, selector) == ACCENT


@pytest.mark.skipif(shutil.which("sassc") is None, reason="needs sassc")
@pytest.mark.parametrize(
    "selector",
    [
        "treeview.view:selected:not(.progressbar):not(.trough)",
        ".nemo-window .view:selected",
    ],
)
def test_graphite_tints_a_selected_file_with_the_accent(
    selector: str, tmp_path: Path
) -> None:
    """Upstream marks a selected row in a list with a grey wash, which outranks
    the accent tint it gives Files; found by hand on the VM. Review of #274:
    the tint, as in Files' icon view and in Orchis and Colloid, not a fill."""
    css = compiled("graphite", THEME, tmp_path)
    assert fill(css, selector) == (ACCENT, 0.2)


@pytest.mark.skipif(shutil.which("sassc") is None, reason="needs sassc")
@pytest.mark.parametrize(
    "theme_name", ["rose-pine", "rose-pine-dawn", "osiris-obsidian", "nord"]
)
def test_text_on_graphites_tinted_row_is_legible(
    theme_name: str, tmp_path: Path
) -> None:
    """Review of #274: accent text on the accent tint fell below AA on light
    Themes, in every GTK 3 list, not only Files'."""
    theme = json.loads((ROOT / "shell" / "themes" / f"{theme_name}.json").read_text())
    css = compiled("graphite", theme, tmp_path)
    named = dict(re.findall(r"@define-color\s+(\w+)\s+([^;]+);", css))
    row = declared(css, "treeview.view:selected:not(.progressbar):not(.trough)")
    tint, alpha = parse(row["background-color"], named)
    ground = rgb(theme["colors"]["background"])
    seen = tuple(t * alpha + g * (1 - alpha) for t, g in zip(tint, ground, strict=True))
    assert contrast(parse(row["color"], named)[0], seen) >= LEGIBLE


@pytest.mark.skipif(shutil.which("sassc") is None, reason="needs sassc")
def test_graphite_keeps_the_files_sidebar_plain(tmp_path: Path) -> None:
    """Upstream's styled sidebar fills all of Files' sidebar with the accent.
    Review of #274: checking one selector passed once that rule was gone."""
    css = compiled("graphite", THEME, tmp_path)
    fill = re.compile(rf"background(-color)?:\s*{THEME['colors']['accent']}")
    painted = [
        selectors
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
        if ".nemo-window" in selectors
        and ".sidebar" in selectors
        and ":selected" not in selectors
        and fill.search(body)
    ]
    assert painted == []
