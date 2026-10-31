"""The desktop defaults provision/cinnamon.py writes for every account."""

from __future__ import annotations

import configparser
import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "provision" / "cinnamon.py"


@pytest.fixture
def cinnamon(monkeypatch: pytest.MonkeyPatch) -> Iterator[ModuleType]:
    # The script puts provision/ on the path and imports its neighbours by bare
    # names such as `run` and `themes`, which would shadow names other tests use.
    monkeypatch.setattr(sys, "path", list(sys.path))
    before = set(sys.modules)
    spec = importlib.util.spec_from_file_location("cinnamon", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yield module
    for name in set(sys.modules) - before:
        del sys.modules[name]


def sections(keyfile: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str  # type: ignore[assignment,method-assign]
    parser.read_string(keyfile)
    return parser


def test_super_s_belongs_to_the_skin_switcher_alone(cinnamon: ModuleType) -> None:
    defaults = sections(cinnamon.dconf_defaults())
    switcher = "org/cinnamon/desktop/keybindings/custom-keybindings/custom3"
    assert defaults[switcher]["binding"] == "['<Super>s']"
    assert defaults["org/cinnamon/desktop/keybindings"]["show-desklets"] == "@as []"
