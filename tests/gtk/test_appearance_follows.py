"""Appearance's Theme list follows Themes added, removed or applied by
someone else while it is open, typically Osiris working from a prompt."""

from __future__ import annotations

import json
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


def a_theme(main: ModuleType, name: str, label: str) -> dict[str, Any]:
    theme = json.loads(Path(main.engine.REPO_THEMES, "nord.json").read_text())
    return {**theme, "name": name, "label": label}


def names(shown: Any) -> list[str]:
    return [card.theme["name"] for card in shown.cards]


def test_a_theme_made_elsewhere_joins_the_list(main: ModuleType) -> None:
    """Filming a demo: Osiris made "Ink and Silence" while Appearance was
    open, and the list still said 8 themes until Appearance was reopened."""
    shown = window(main)
    main.engine.save(a_theme(main, "ink-and-silence", "Ink and Silence"))
    assert settle(lambda: "ink-and-silence" in names(shown), seconds=10)


def test_a_theme_deleted_elsewhere_leaves_the_list(main: ModuleType) -> None:
    main.engine.save(a_theme(main, "ink-duel", "Ink Duel"))
    shown = window(main)
    assert "ink-duel" in names(shown)
    main.engine.delete("ink-duel")
    assert settle(lambda: "ink-duel" not in names(shown))


def test_a_theme_applied_on_a_new_account_is_selected(
    main: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review of #259: with no ~/.config/osiris yet, the record was watched
    before the Theme folder made it, and GLib only polls for a missing folder."""
    engine = main.engine
    osiris = tmp_path / "config" / "osiris"
    monkeypatch.setattr(engine, "SEARCH", [str(osiris / "themes"), engine.REPO_THEMES])
    monkeypatch.setattr(engine, "STATE", str(osiris / "theme"))
    shown = window(main)
    (osiris / "theme").write_text("rose-pine\n")
    assert settle(lambda: selected(shown) == ["rose-pine"])
