"""Camo, the still wallpaper style that replaced Contour: blobs of the Theme's
tones with the accent laid down in patches of its own."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "shell" / "themes" / "wallpaper.py"


@pytest.fixture
def wallpaper(monkeypatch: pytest.MonkeyPatch) -> Iterator[ModuleType]:
    # The script puts shell/themes/ on the path and imports `paths` by its bare
    # name, which would shadow names other tests use.
    monkeypatch.setattr(sys, "path", list(sys.path))
    before = set(sys.modules)
    spec = importlib.util.spec_from_file_location("wallpaper", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yield module
    for name in set(sys.modules) - before:
        del sys.modules[name]


def test_camo_lays_the_accent_down_in_patches(wallpaper: ModuleType) -> None:
    """Every other still style keeps the accent to hairlines."""
    _, accent = wallpaper.camo((180, 320), np.random.default_rng(1))
    patches = accent > 0.5
    assert ((accent > 0) & (accent < 1)).mean() < 0.05
    assert 0.05 < patches.mean() < 0.4
    assert wallpaper._edges(patches).sum() < 0.2 * patches.sum()


def test_camo_is_offered_where_contour_was(wallpaper: ModuleType) -> None:
    """The person never wants Contour again. Camo takes its place first in the
    list and among the styles a Theme naming none falls back to."""
    assert wallpaper.STYLES[0] == "camo"
    assert "contour" not in wallpaper.styles()
    assert wallpaper.FALLBACK_STYLES == ("camo", "arcs", "strata")


THEME = {
    "name": "camo-test",
    "dark": True,
    "colors": {"background": "#15151c", "accent": "#7aa2f7", "foreground": "#c0caf5"},
}


def test_camo_keeps_its_edges_crisp_away_from_the_mark(
    wallpaper: ModuleType,
) -> None:
    """The quiet mask fades every style towards the middle, which blurred
    Camo's blobs into smudges when tried. A row of crisp camo is almost all
    its five tones, with only the edges between them."""
    image = np.asarray(wallpaper.compose(THEME, (640, 360), "camo", logo=False))
    _, counts = np.unique(image[108].reshape(-1, 3), axis=0, return_counts=True)
    assert np.sort(counts)[-5:].sum() >= 0.95 * 640


def test_a_theme_that_names_contour_gets_camo(wallpaper: ModuleType) -> None:
    """Themes made before Camo name Contour, the Theme creator's old default."""
    contour = {**THEME, "wallpaper_style": "contour"}
    camo = {**THEME, "wallpaper_style": "camo"}
    assert np.array_equal(
        np.asarray(wallpaper.compose(contour, (320, 180), logo=False)),
        np.asarray(wallpaper.compose(camo, (320, 180), logo=False)),
    )


def test_camo_blends_its_edges_over_about_a_pixel(wallpaper: ModuleType) -> None:
    """Hard thresholds alias into stairs, plainest in the Theme creator's
    small previews; found by hand."""
    _, accent = wallpaper.camo((180, 320), np.random.default_rng(1))
    edges = wallpaper._edges(accent > 0.5).sum()
    assert ((accent > 0.05) & (accent < 0.95)).sum() > 0.5 * edges


def test_contour_asked_for_by_name_is_camo(wallpaper: ModuleType) -> None:
    """Review of #275: a style passed in directly skipped the theme's lookup and
    raised for Contour."""
    assert np.array_equal(
        np.asarray(wallpaper.compose(THEME, (320, 180), "contour", logo=False)),
        np.asarray(wallpaper.compose(THEME, (320, 180), "camo", logo=False)),
    )


def test_a_theme_that_names_contour_boots_on_camo(wallpaper: ModuleType) -> None:
    """Review of #275: the boot menu's own lookup had no test."""
    contour = {**THEME, "wallpaper_style": "contour"}
    camo = {**THEME, "wallpaper_style": "camo"}
    assert np.array_equal(
        np.asarray(wallpaper.boot_background(contour, (320, 180))),
        np.asarray(wallpaper.boot_background(camo, (320, 180))),
    )
