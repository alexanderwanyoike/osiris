"""Appearance's Theme list follows Themes added, removed or applied by
someone else while it is open, typically Osiris working from a prompt."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from gi.repository import Gio

from .conftest import settle
from .test_appearance_app import appearance


@pytest.fixture
def main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Appearance, with the engine's files for this person in tmp_path."""
    module = appearance()
    engine = module.engine
    themes = tmp_path / "themes"
    assets = tmp_path / "assets"
    monkeypatch.setattr(engine, "SEARCH", [str(themes), engine.REPO_THEMES])
    monkeypatch.setattr(engine, "STATE", str(tmp_path / "theme"))
    monkeypatch.setattr(engine, "FAVOURITES", str(tmp_path / "favourites"))
    monkeypatch.setattr(engine, "USER_ASSETS", str(assets))
    monkeypatch.setattr(engine, "USER_PREVIEWS", str(assets / "previews"))
    monkeypatch.setattr(engine, "USER_WALLPAPERS", str(assets / "wallpapers"))
    monkeypatch.setattr(engine, "ASSET_MANIFEST", str(assets / "assets.json"))
    # The Skins page draws its pictures on a thread, which is not under test.
    monkeypatch.setattr(engine, "stale_skin_pictures", lambda: [])
    (tmp_path / "theme").write_text("nord\n")
    return module


def window(main: ModuleType) -> Any:
    app = main.Application()
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    return main.Window(app)


def selected(shown: Any) -> list[str]:
    return [
        card.theme["name"]
        for card in shown.cards
        if card.button.has_css_class("selected")
    ]


def test_a_theme_applied_elsewhere_is_the_one_selected(
    main: ModuleType, tmp_path: Path
) -> None:
    """Filming a demo: Osiris applied a Theme while Appearance was open, and
    the old Theme's card kept the highlight until Appearance was reopened."""
    shown = window(main)
    assert selected(shown) == ["nord"]
    (tmp_path / "theme").write_text("rose-pine\n")
    assert settle(lambda: selected(shown) == ["rose-pine"])
