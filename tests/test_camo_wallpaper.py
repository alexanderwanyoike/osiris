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
    patches = accent == 1
    assert set(np.unique(accent)) <= {0.0, 1.0}
    assert 0.05 < patches.mean() < 0.4
    assert wallpaper._edges(patches).sum() < 0.2 * patches.sum()
