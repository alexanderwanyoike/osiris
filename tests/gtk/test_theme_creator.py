"""The Theme creator's wallpaper patterns."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from gi.repository import Gtk

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
