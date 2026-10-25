"""Sharing Skins: a skinpack exported as one file, opened from one, and a
person's own Skins deleted (shipped ones cannot be)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from osiris.platform.process import FakeRunner
from osiris.skins.pack import SkinpackError, read
from osiris.skins.share import EXTENSION, delete, duplicate, export, open_file

FIELDS = {"author": "a", "version": "1", "licence": "GPL-3.0", "source": "s"}


def make_pack(root: Path, label: str = "Colloid") -> Path:
    (root / "sass").mkdir(parents=True)
    (root / "skin.json").write_text(json.dumps({"label": label, **FIELDS}))
    (root / "sass" / "_palette.scss").write_text("@import 'gaps';\n")
    return root


def test_an_exported_skin_opens_as_the_same_skin(tmp_path: Path) -> None:
    shared = export(read(make_pack(tmp_path / "shipped" / "colloid")), tmp_path / "out")
    assert shared == tmp_path / "out" / f"colloid{EXTENSION}"
    opened = open_file(shared, tmp_path / "mine")
    assert opened.label == "Colloid"
    assert (tmp_path / "mine" / "colloid" / "sass" / "_palette.scss").is_file()


def test_a_file_without_a_label_is_refused_and_leaves_nothing(tmp_path: Path) -> None:
    junk = tmp_path / f"junk{EXTENSION}"
    with zipfile.ZipFile(junk, "w") as archive:
        archive.writestr("junk/readme.txt", "hello")
    with pytest.raises(SkinpackError):
        open_file(junk, tmp_path / "mine")
    assert not (tmp_path / "mine" / "junk").exists()


def test_a_file_reaching_outside_its_folder_is_refused(tmp_path: Path) -> None:
    evil = tmp_path / f"evil{EXTENSION}"
    with zipfile.ZipFile(evil, "w") as archive:
        archive.writestr("evil/skin.json", json.dumps({"label": "Evil", **FIELDS}))
        archive.writestr("evil/../../escaped.txt", "out")
    with pytest.raises(SkinpackError):
        open_file(evil, tmp_path / "mine")
    assert not (tmp_path / "escaped.txt").exists()


def test_a_persons_skin_can_be_deleted(tmp_path: Path) -> None:
    pack = read(make_pack(tmp_path / "mine" / "colloid"))
    delete(pack, tmp_path / "mine")
    assert not (tmp_path / "mine" / "colloid").exists()


def test_a_shipped_skin_cannot_be_deleted(tmp_path: Path) -> None:
    pack = read(make_pack(tmp_path / "shipped" / "colloid"))
    with pytest.raises(SkinpackError, match="ships with Osiris"):
        delete(pack, tmp_path / "mine")
    assert (tmp_path / "shipped" / "colloid").exists()


def test_a_duplicate_is_a_persons_own_copy_under_a_new_name(tmp_path: Path) -> None:
    pack = read(make_pack(tmp_path / "shipped" / "colloid"))
    copy = duplicate(pack, tmp_path / "mine", FakeRunner())
    assert copy.name == "colloid-copy"
    assert copy.label == "Colloid (copy)"
    assert copy.root == tmp_path / "mine" / "colloid-copy"
    assert (copy.root / "sass" / "_palette.scss").is_file()


def test_duplicating_twice_finds_a_free_name(tmp_path: Path) -> None:
    pack = read(make_pack(tmp_path / "shipped" / "colloid"))
    duplicate(pack, tmp_path / "mine", FakeRunner())
    assert duplicate(pack, tmp_path / "mine", FakeRunner()).name == "colloid-copy-2"


def test_a_duplicate_tells_osiris_how_to_change_it(tmp_path: Path) -> None:
    pack = read(make_pack(tmp_path / "shipped" / "colloid"))
    copy = duplicate(pack, tmp_path / "mine", FakeRunner())
    agents = (copy.root / "AGENTS.md").read_text()
    assert "--skin colloid-copy" in agents
    assert "$gap-accent" in agents


def test_a_duplicate_keeps_its_history_so_changes_can_be_undone(tmp_path: Path) -> None:
    runner = FakeRunner()
    copy = duplicate(
        read(make_pack(tmp_path / "shipped" / "colloid")), tmp_path / "mine", runner
    )
    assert runner.ran("git", "-C", str(copy.root), "init", "-q")
    assert runner.ran("git", "-C", str(copy.root), "add", "-A")
    assert runner.ran("git", "-C", str(copy.root), "commit", "-q")
