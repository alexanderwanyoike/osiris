"""The Theme creator's wallpaper patterns."""

from __future__ import annotations

from pathlib import Path

import pytest
from gi.repository import Gtk

from .conftest import APPS

THEMES = Path(__file__).resolve().parents[2] / "shell" / "themes"


def test_a_new_theme_starts_on_camo_and_says_so(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Camo replaced Contour, the old starting pattern; the person never wants
    Contour again."""
    monkeypatch.syspath_prepend(str(THEMES))
    monkeypatch.syspath_prepend(str(APPS / "appearance"))
    import creator

    dialog = creator.Creator(Gtk.Window(), lambda *_args: None)
    patterns = dialog.style.get_model()
    labels = [patterns.get_string(i) for i in range(patterns.get_n_items())]
    assert labels[dialog.style.get_selected()].startswith("Camo - ")
    assert not any("Contour" in label for label in labels)
