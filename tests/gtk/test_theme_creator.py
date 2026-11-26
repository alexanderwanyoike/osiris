"""The Theme creator's wallpaper patterns."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from gi.repository import Adw, Gtk

from .conftest import settle, widgets

THEMES = Path(__file__).resolve().parents[2] / "shell" / "themes"


@pytest.fixture
def creator(monkeypatch: pytest.MonkeyPatch) -> Iterator[ModuleType]:
    # The creator imports shell/themes/ modules by bare names, such as `paths`
    # and `wallpaper`, which would shadow names other tests use.
    monkeypatch.syspath_prepend(str(THEMES))
    before = set(sys.modules)
    import creator as module

    yield module
    # Only modules loaded from the repository, since numpy cannot load twice.
    root = str(THEMES.parents[1])
    for name in set(sys.modules) - before:
        if (getattr(sys.modules[name], "__file__", None) or "").startswith(root):
            del sys.modules[name]


def test_a_new_theme_starts_on_camo_and_says_so(creator: ModuleType) -> None:
    """Camo replaced Contour, the old starting pattern; the person never wants
    Contour again."""
    dialog = creator.Creator(Gtk.Window(), lambda *_args: None)
    patterns = dialog.style.get_model()
    labels = [patterns.get_string(i) for i in range(patterns.get_n_items())]
    assert labels[dialog.style.get_selected()].startswith("Camo - ")
    assert not any("Contour" in label for label in labels)


def test_camos_label_fits_the_pattern_row(creator: ModuleType) -> None:
    """Review of #275: the label was cut off twice, found by hand."""
    window = Adw.ApplicationWindow(default_width=1000, default_height=900)
    window.present()
    dialog = creator.Creator(window, lambda *_args: None)
    dialog.present(window)
    shown = [
        label
        for label in widgets(dialog.style)
        if isinstance(label, Gtk.Label) and label.get_text().startswith("Camo")
    ]
    assert settle(lambda: bool(shown) and shown[0].get_width() > 0)
    ellipsized = shown[0].get_layout().is_ellipsized()
    window.destroy()
    assert not ellipsized
