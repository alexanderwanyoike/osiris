"""Which Skins there are, and which one the person chose."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from osiris.skins.library import (
    OSIRIS,
    available,
    choose,
    chosen,
    find,
    styles,
    wear_choice,
)
from osiris.skins.pack import SkinpackError


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


def test_a_skin_with_a_broken_label_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "shipped" / "broken").mkdir(parents=True)
    (tmp_path / "shipped" / "broken" / "skin.json").write_text("[]")
    make_pack(tmp_path / "shipped" / "colloid", "Colloid")
    assert [pack.name for pack in available([tmp_path / "shipped"])] == ["colloid"]


def test_finding_the_osiris_skin_gives_no_pack(tmp_path: Path) -> None:
    make_pack(tmp_path / "shipped" / "colloid", "Colloid")
    assert find([tmp_path / "shipped"], OSIRIS) is None
    found = find([tmp_path / "shipped"], "colloid")
    assert found is not None and found.label == "Colloid"


def test_any_skin_but_the_one_being_edited_can_be_a_style(tmp_path: Path) -> None:
    """A person's own Skins are styles too, so a new style never needs to be
    installed among the shipped ones, which belong to the system."""
    mine, shipped = tmp_path / "mine", tmp_path / "shipped"
    make_pack(mine / "yaru", "Yaru Colors")
    make_pack(mine / "old-forest", "Old Forest")
    make_pack(shipped / "colloid", "Colloid")
    names = [pack.name for pack in styles([mine, shipped], editing="old-forest")]
    assert names == ["yaru", "colloid"]


def test_a_skin_worn_is_the_one_chosen(tmp_path: Path) -> None:
    worn: list[str] = []

    def apply() -> SkinpackError | None:
        worn.append(chosen(tmp_path / "skin"))
        return None

    wear_choice(tmp_path / "skin", "colloid", apply)
    assert worn == ["colloid"]
    assert chosen(tmp_path / "skin") == "colloid"


def test_a_skin_that_could_not_be_worn_is_reported_and_not_chosen(
    tmp_path: Path,
) -> None:
    """The desktop fell back to Osiris's own look; the choice says so, so
    Appearance does not tick a Skin nobody sees."""
    with pytest.raises(SkinpackError, match="bad sheet"):
        wear_choice(
            tmp_path / "skin", "colloid", lambda: SkinpackError("Colloid: bad sheet")
        )
    assert chosen(tmp_path / "skin") == OSIRIS
