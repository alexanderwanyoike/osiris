"""When a Skin's picture must be drawn again: it is kept per Skin and Theme,
and drawn again once anything it shows changes."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from osiris.skins.pictures import (
    cursor_picture,
    draw,
    failed,
    needs_drawing,
    picture_for,
    sampler_env,
    signature,
)


def touch(path: Path, when: float) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x")
    os.utime(path, (when, when))
    return path


def skin(root: Path) -> list[Path]:
    """What a picture of a Skin in a Theme shows."""
    touch(root / "pack" / "sass" / "_palette.scss", 100)
    return [root / "pack", touch(root / "nord.json", 100)]


def test_each_skin_and_theme_has_a_picture_of_its_own(tmp_path: Path) -> None:
    shows = skin(tmp_path)
    nord = picture_for(tmp_path / "cache", "colloid", "nord", shows)
    assert nord != picture_for(tmp_path / "cache", "colloid", "rose-pine", shows)
    assert tmp_path / "cache" in nord.parents


def test_a_picture_not_yet_drawn_needs_drawing(tmp_path: Path) -> None:
    picture = picture_for(tmp_path / "cache", "colloid", "nord", skin(tmp_path))
    assert needs_drawing(picture)
    picture.parent.mkdir(parents=True)
    picture.write_bytes(b"png")
    assert not needs_drawing(picture)


def test_a_change_to_what_it_shows_needs_a_new_picture(tmp_path: Path) -> None:
    shows = skin(tmp_path)
    before = picture_for(tmp_path / "cache", "colloid", "nord", shows)
    (tmp_path / "pack" / "sass" / "_palette.scss").write_text("changed")
    after = picture_for(tmp_path / "cache", "colloid", "nord", shows)
    assert after != before
    assert needs_drawing(after)


def test_a_picture_that_failed_is_not_drawn_again_until_what_it_shows_changes(
    tmp_path: Path,
) -> None:
    """Review of #133: a failed picture stayed stale, so Appearance drew it
    again as soon as it finished, forever."""
    shows = skin(tmp_path)
    picture = picture_for(tmp_path / "cache", "colloid", "nord", shows)
    failed(picture)
    assert not needs_drawing(picture)
    (tmp_path / "pack" / "sass" / "_palette.scss").write_text("changed")
    assert needs_drawing(picture_for(tmp_path / "cache", "colloid", "nord", shows))


def test_a_picture_appears_only_once_it_is_whole(tmp_path: Path) -> None:
    """Review of #133: the sampler wrote straight to the picture, so the
    page could show one half written."""
    picture = picture_for(tmp_path / "cache", "colloid", "nord", skin(tmp_path))
    seen: list[bool] = []

    def drawer(out: Path) -> None:
        out.write_bytes(b"half")
        seen.append(picture.exists())
        out.write_bytes(b"whole")

    draw(picture, drawer)
    assert seen == [False]
    assert picture.read_bytes() == b"whole"


def test_a_picture_that_fails_leaves_nothing_half_drawn(tmp_path: Path) -> None:
    picture = picture_for(tmp_path / "cache", "colloid", "nord", skin(tmp_path))

    def drawer(out: Path) -> None:
        out.write_bytes(b"half")
        raise RuntimeError("the sampler crashed")

    with pytest.raises(RuntimeError):
        draw(picture, drawer)
    assert not list(picture.parent.glob("*.png"))


def test_a_new_picture_replaces_the_ones_it_supersedes(tmp_path: Path) -> None:
    """Review of #133: every change to a Skin or Theme left another picture
    in the cache for good."""
    shows = skin(tmp_path)
    old = picture_for(tmp_path / "cache", "colloid", "nord", shows)
    draw(old, lambda out: out.write_bytes(b"old"))
    other = picture_for(tmp_path / "cache", "colloid", "rose-pine", shows)
    draw(other, lambda out: out.write_bytes(b"other"))
    (tmp_path / "pack" / "sass" / "_palette.scss").write_text("changed")
    new = picture_for(tmp_path / "cache", "colloid", "nord", shows)
    failed(new)
    draw(new, lambda out: out.write_bytes(b"new"))
    assert list(new.parent.iterdir()) == [new]
    assert other.is_file()


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


def test_the_sampler_finds_the_built_theme_without_hiding_the_persons_own(
    tmp_path: Path,
) -> None:
    """Review of #133: pointing XDG_DATA_HOME at the cache hid the person's
    icons and fonts in ~/.local/share from the picture."""
    env = sampler_env({"XDG_DATA_HOME": "/home/me/.local/share"}, tmp_path)
    assert env["XDG_DATA_HOME"] == "/home/me/.local/share"
    assert env["XDG_DATA_DIRS"] == f"{tmp_path}:/usr/local/share:/usr/share"


def test_the_systems_data_folders_are_kept_after_the_built_theme(
    tmp_path: Path,
) -> None:
    env = sampler_env({"XDG_DATA_DIRS": "/opt/share:/usr/share"}, tmp_path)
    assert env["XDG_DATA_DIRS"] == f"{tmp_path}:/opt/share:/usr/share"


def test_what_a_picture_shows_is_signed_by_content_not_by_time(tmp_path: Path) -> None:
    """Review of #133: by modification time, a Skin merely touched, or one
    whose history moved on, had its picture drawn again."""
    pack = tmp_path / "pack"
    touch(pack / "sass" / "_palette.scss", 100)
    theme = touch(tmp_path / "nord.json", 100)
    before = signature([pack, theme])
    touch(pack / "sass" / "_palette.scss", 300)
    touch(pack / ".git" / "HEAD", 300)
    assert signature([pack, theme]) == before
    (pack / "sass" / "_palette.scss").write_text("changed")
    assert signature([pack, theme]) != before
