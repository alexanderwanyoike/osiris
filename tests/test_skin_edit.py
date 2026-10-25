"""Editing a person's Skin: its name, the style it is built on, and the icons,
cursor and font it wears. Each save is a commit, so it can be undone."""

from __future__ import annotations

import json
from pathlib import Path

from osiris.model.author import as_osiris
from osiris.platform.process import FakeRunner
from osiris.skins.edit import Edit, save
from osiris.skins.pack import read
from osiris.skins.share import duplicate

FIELDS = {"version": "1", "licence": "GPL-3.0", "source": "s"}


def make_pack(root: Path, label: str, author: str, palette: str) -> Path:
    (root / "sass").mkdir(parents=True)
    (root / "skin.json").write_text(
        json.dumps({"label": label, "author": author, **FIELDS})
    )
    (root / "sass" / "_palette.scss").write_text(palette)
    return root


def mine(tmp_path: Path) -> Path:
    shipped = read(
        make_pack(tmp_path / "shipped" / "colloid", "Colloid", "Vince", "colloid")
    )
    return duplicate(shipped, tmp_path / "mine", FakeRunner(), label="Sharp").root


def keep(label: str = "Sharp") -> Edit:
    return Edit(label=label, style=None, icons=None, cursor=None, font=None)


def test_renaming_keeps_the_skin_where_it_is(tmp_path: Path) -> None:
    root = mine(tmp_path)
    renamed = save(read(root), keep("Sharp Night"), FakeRunner())
    assert (renamed.name, renamed.label) == ("sharp", "Sharp Night")


def test_icons_cursor_and_font_are_worn_with_the_skin(tmp_path: Path) -> None:
    root = mine(tmp_path)
    edit = Edit("Sharp", None, icons="Papirus", cursor="Bibata", font="Inter 10")
    edited = save(read(root), edit, FakeRunner())
    assert edited.look("dark").icons == "Papirus"
    assert (edited.look("light").cursor, edited.look("light").font) == (
        "Bibata",
        "Inter 10",
    )


def test_leaving_a_choice_empty_keeps_the_themes(tmp_path: Path) -> None:
    root = mine(tmp_path)
    save(read(root), Edit("Sharp", None, "Papirus", None, None), FakeRunner())
    edited = save(read(root), keep(), FakeRunner())
    assert edited.look("dark").icons is None
    assert "look" not in json.loads((root / "skin.json").read_text())


def test_a_new_style_brings_its_sheets_and_credits_and_keeps_the_rest(
    tmp_path: Path,
) -> None:
    root = mine(tmp_path)
    graphite = read(
        make_pack(tmp_path / "shipped" / "graphite", "Graphite", "Vince L", "graphite")
    )
    edit = Edit("Sharp", graphite, icons="Papirus", cursor=None, font=None)
    edited = save(read(root), edit, FakeRunner())
    assert (root / "sass" / "_palette.scss").read_text() == "graphite"
    assert (edited.label, edited.author, edited.style) == (
        "Sharp",
        "Vince L",
        "graphite",
    )
    assert edited.look("dark").icons == "Papirus"
    assert "--skin sharp" in (root / "AGENTS.md").read_text()


def test_a_save_is_committed_as_osiris(tmp_path: Path) -> None:
    root, runner = mine(tmp_path), FakeRunner()
    save(read(root), keep("Sharp Night"), runner)
    assert runner.ran("git", "-C", str(root), "add", "-A")
    assert runner.ran("git", "-C", str(root), *as_osiris(), "commit", "-q")


def test_a_copy_remembers_the_style_it_came_from(tmp_path: Path) -> None:
    assert read(mine(tmp_path)).style == "colloid"
