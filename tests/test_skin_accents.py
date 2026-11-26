"""Jasper and Graphite mark a selected file in the Theme's accent and keep Files'
sidebar plain, as the other shipped Skins do."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from tests.test_skin_contrast import compiled, declared, parse, rgb

ROOT = Path(__file__).resolve().parent.parent
THEME = json.loads((ROOT / "shell" / "themes" / "osiris-obsidian.json").read_text())
ACCENT = rgb(THEME["colors"]["accent"])


def colour(css: str, selector: str) -> tuple[float, ...]:
    named = dict(re.findall(r"@define-color\s+(\w+)\s+([^;]+);", css))
    return parse(declared(css, selector)["background-color"], named)[0]


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
def test_graphite_fills_a_selected_file_with_the_accent(tmp_path: Path) -> None:
    """Upstream marks a selected row in a list with a grey wash, and that rule
    outranks its accent tint for Files; found by hand on the VM."""
    css = compiled("graphite", THEME, tmp_path)
    selector = "treeview.view:selected:not(.progressbar):not(.trough)"
    assert colour(css, selector) == ACCENT


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
