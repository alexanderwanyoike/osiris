"""Which Skins there are, and which one the person chose."""

from __future__ import annotations

import json
from pathlib import Path

from osiris.skins.library import OSIRIS, available, choose, chosen, find


def make_pack(root: Path, label: str) -> None:
    root.mkdir(parents=True)
    fields = {"author": "a", "version": "1", "licence": "GPL-3.0", "source": "s"}
    (root / "skin.json").write_text(json.dumps({"label": label, **fields}))


def test_nothing_chosen_means_the_osiris_skin(tmp_path: Path) -> None:
    assert chosen(tmp_path / "skin") == OSIRIS


def test_a_choice_is_remembered(tmp_path: Path) -> None:
    choose(tmp_path / "config" / "skin", "colloid")
    assert chosen(tmp_path / "config" / "skin") == "colloid"


def test_a_persons_skin_overrides_a_shipped_one_of_the_same_name(
    tmp_path: Path,
) -> None:
    mine, shipped = tmp_path / "mine", tmp_path / "shipped"
    make_pack(mine / "colloid", "My Colloid")
    make_pack(shipped / "colloid", "Colloid")
    make_pack(shipped / "graphite", "Graphite")
    labels = [pack.label for pack in available([mine, shipped])]
    assert labels == ["My Colloid", "Graphite"]


def test_folders_that_are_not_skinpacks_are_skipped(tmp_path: Path) -> None:
    (tmp_path / "shipped" / "junk").mkdir(parents=True)
    make_pack(tmp_path / "shipped" / "colloid", "Colloid")
    assert [pack.name for pack in available([tmp_path / "shipped"])] == ["colloid"]


def test_finding_the_osiris_skin_gives_no_pack(tmp_path: Path) -> None:
    make_pack(tmp_path / "shipped" / "colloid", "Colloid")
    assert find([tmp_path / "shipped"], OSIRIS) is None
    found = find([tmp_path / "shipped"], "colloid")
    assert found is not None and found.label == "Colloid"
