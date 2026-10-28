"""When a Skin's picture must be drawn again: it is kept per Skin and Theme,
and redrawn once the Skin or the Theme changes after it."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from osiris.skins.pictures import (
    cursor_picture,
    failed,
    is_fresh,
    needs_drawing,
    picture_for,
)


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


def test_a_picture_that_failed_is_not_drawn_again_until_its_skin_changes(
    tmp_path: Path,
) -> None:
    """Review of #133: a failed picture stayed stale, so Appearance drew it
    again as soon as it finished, forever."""
    pack = tmp_path / "pack"
    touch(pack / "sass" / "_palette.scss", 100)
    picture = tmp_path / "colloid--nord.png"
    assert needs_drawing(picture, [pack])
    failed(picture)
    assert not needs_drawing(picture, [pack])
    touch(pack / "sass" / "_palette.scss", time.time() + 60)
    assert needs_drawing(picture, [pack])


def test_a_cursors_picture_is_kept_in_the_cache(tmp_path: Path) -> None:
    assert cursor_picture(tmp_path, "Bibata", "left_ptr").parent == tmp_path


@pytest.mark.parametrize("name", ["../../evil", "a/b", "..", ".", ""])
def test_a_cursor_name_that_is_not_a_plain_name_is_refused(
    tmp_path: Path, name: str
) -> None:
    """Review of #133: a Skin's look naming its cursor ../../x wrote the
    picture outside the cache."""
    with pytest.raises(ValueError):
        cursor_picture(tmp_path, name, "left_ptr")
