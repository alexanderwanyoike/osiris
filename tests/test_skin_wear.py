"""Wearing a Skin: what it carries installed, then built in a Theme's colours."""

from __future__ import annotations

import json
from pathlib import Path

from osiris.platform.process import FakeRunner
from osiris.skins.pack import Look, read
from osiris.skins.wear import Places, wear

ROSE_PINE = {
    "name": "rose-pine",
    "dark": True,
    "colors": {
        "background": "#191724",
        "surface": "#1f1d2e",
        "foreground": "#e0def4",
        "accent": "#c4a7e7",
        "success": "#9ccfd8",
        "warning": "#f6c177",
        "danger": "#eb6f92",
    },
}


def make_pack(root: Path, files: dict[str, str] | None = None) -> Path:
    label = {"label": "Plain", "author": "a", "version": "1", "licence": "GPL-3.0"}
    look = {"icons": {"light": "Plain-Light", "dark": "Plain-Dark"}}
    for path, text in {
        "skin.json": json.dumps({**label, "source": "s", "look": look}),
        "gtk-3.0/gtk-dark.scss": "",
        **(files or {}),
    }.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)
    return root


def places(tmp_path: Path) -> Places:
    return Places(
        themes=tmp_path / "themes",
        work=tmp_path / "work",
        icons=tmp_path / "icons",
        fonts=tmp_path / "fonts",
    )


def test_a_skin_without_its_own_panel_gets_osiris_own(tmp_path: Path) -> None:
    panels: list[Path] = []
    wear(
        read(make_pack(tmp_path / "plain")),
        ROSE_PINE,
        places(tmp_path),
        FakeRunner(),
        panels.append,
    )
    assert panels == [tmp_path / "themes" / "Osiris-plain-rose-pine"]


def test_a_skin_with_its_own_panel_keeps_it(tmp_path: Path) -> None:
    panels: list[Path] = []
    pack = read(make_pack(tmp_path / "plain", {"cinnamon/cinnamon-dark.scss": ""}))
    wear(pack, ROSE_PINE, places(tmp_path), FakeRunner(), panels.append)
    assert panels == []


def test_new_fonts_refresh_the_font_cache(tmp_path: Path) -> None:
    runner = FakeRunner()
    pack = read(make_pack(tmp_path / "plain", {"fonts/Inter.ttf": "font"}))
    wear(pack, ROSE_PINE, places(tmp_path), runner, lambda _theme: None)
    assert runner.ran("fc-cache", "-f", str(tmp_path / "fonts"))


def test_the_skin_is_worn_with_its_look_for_the_themes_variant(
    tmp_path: Path,
) -> None:
    built, look = wear(
        read(make_pack(tmp_path / "plain")),
        ROSE_PINE,
        places(tmp_path),
        FakeRunner(),
        lambda _theme: None,
    )
    assert built.theme == "Osiris-plain-rose-pine"
    assert look == Look("Plain-Dark", None, None)
