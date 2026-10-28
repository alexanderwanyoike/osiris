"""What the scripts that make the shipped Skins from upstream share: an edit to
upstream that no longer applies stops the script instead of passing silently."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

MAKERS = Path(__file__).resolve().parent.parent / "shell" / "skins" / "makers.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("makers", MAKERS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_replacement_that_matches_nothing_stops_the_maker() -> None:
    makers = load()
    with pytest.raises(SystemExit, match=r"upstream changed: '156' not in on\(\)"):
        makers.replace("@if ($b >= 128)", "156", "$mid", "on()")
