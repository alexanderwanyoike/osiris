"""A skinpack: a Skin's label and style sheets, with gaps for the Theme's colours."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from osiris.skins.pack import SkinpackError, fill, gaps, read, sass_gaps

LABEL = {
    "label": "Colloid",
    "author": "Vince Liuice",
    "version": "2026-08-23",
    "licence": "GPL-3.0",
    "source": "https://github.com/vinceliuice/Colloid-gtk-theme",
}


def make_pack(root: Path, label: dict[str, str]) -> Path:
    root.mkdir()
    (root / "skin.json").write_text(json.dumps(label))
    return root


def test_reads_the_label_and_takes_its_name_from_the_folder(tmp_path: Path) -> None:
    pack = read(make_pack(tmp_path / "colloid", LABEL))
    assert pack.name == "colloid"
    assert pack.label == "Colloid"
    assert pack.licence == "GPL-3.0"
    assert pack.root == tmp_path / "colloid"


def test_a_folder_without_a_label_is_not_a_skinpack(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    with pytest.raises(SkinpackError, match=r"skin\.json"):
        read(tmp_path / "empty")


def test_a_label_missing_a_field_says_which(tmp_path: Path) -> None:
    label = {k: v for k, v in LABEL.items() if k != "licence"}
    with pytest.raises(SkinpackError, match="licence"):
        read(make_pack(tmp_path / "colloid", label))


ROSE_PINE = {
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


def test_a_themes_roles_fill_the_gaps() -> None:
    filled = fill("a { color: {{accent}}; background: {{background}}; }", gaps(ROSE_PINE))
    assert filled == "a { color: #c4a7e7; background: #191724; }"


def test_plank_gaps_take_its_own_colour_format() -> None:
    assert fill("Fill={{background_plank}}", gaps(ROSE_PINE)) == "Fill=25;;23;;36;;255"


def test_an_unknown_gap_is_an_error_not_a_broken_sheet() -> None:
    with pytest.raises(SkinpackError, match="glow"):
        fill("a { color: {{glow}}; }", gaps(ROSE_PINE))


def test_sass_reads_the_gaps_as_variables() -> None:
    sass = sass_gaps(gaps(ROSE_PINE))
    assert "$gap-accent: #c4a7e7;" in sass
    assert "$gap-variant: 'dark';" in sass
