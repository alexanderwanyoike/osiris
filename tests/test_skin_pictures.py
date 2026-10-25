"""When a Skin's picture must be drawn again: it is kept per Skin and Theme,
and redrawn once the Skin or the Theme changes after it."""

from __future__ import annotations

import os
from pathlib import Path

from osiris.skins.pictures import is_fresh, picture_for


def touch(path: Path, when: float) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x")
    os.utime(path, (when, when))
    return path


def test_each_skin_and_theme_has_a_picture_of_its_own(tmp_path: Path) -> None:
    assert picture_for(tmp_path, "colloid", "nord") != picture_for(
        tmp_path, "colloid", "rose-pine"
    )
    assert picture_for(tmp_path, "colloid", "nord").parent == tmp_path


def test_a_missing_picture_is_not_fresh(tmp_path: Path) -> None:
    source = touch(tmp_path / "pack" / "skin.json", 100)
    assert not is_fresh(tmp_path / "missing.png", [source])


def test_a_picture_newer_than_everything_it_shows_is_fresh(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    touch(pack / "sass" / "_palette.scss", 100)
    theme = touch(tmp_path / "nord.json", 100)
    picture = touch(tmp_path / "colloid--nord.png", 200)
    assert is_fresh(picture, [pack, theme])


def test_a_change_deep_in_the_skin_makes_it_stale(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    touch(pack / "sass" / "_palette.scss", 300)
    picture = touch(tmp_path / "colloid--nord.png", 200)
    assert not is_fresh(picture, [pack])
