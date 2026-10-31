"""A skinpack: a Skin's label and style sheets, with gaps for the Theme's colours."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from osiris.skins.pack import Look, SkinpackError, fill, gaps, read, sass_gaps

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


@pytest.mark.parametrize(
    "content",
    [b"{not json", b"[]", b'"Colloid"', b'{"label": "Caf\xe9"}', b"{}"],
)
def test_a_malformed_label_is_a_skinpack_error(tmp_path: Path, content: bytes) -> None:
    """Anything else escapes the listing that skips broken Skins, and with it
    every Theme switch and login."""
    root = tmp_path / "colloid"
    root.mkdir()
    (root / "skin.json").write_bytes(content)
    with pytest.raises(SkinpackError, match=r"skin\.json"):
        read(root)


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
    filled = fill(
        "a { color: {{accent}}; background: {{background}}; }", gaps(ROSE_PINE)
    )
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


def test_a_pack_may_name_its_icons_cursor_and_font(tmp_path: Path) -> None:
    look = {
        "icons": {"light": "Colloid-Light", "dark": "Colloid-Dark"},
        "cursor": "Colloid-cursors",
        "font": "Inter 10",
    }
    pack = read(make_pack(tmp_path / "colloid", {**LABEL, "look": look}))
    assert pack.look("dark") == Look("Colloid-Dark", "Colloid-cursors", "Inter 10")
    assert pack.look("light").icons == "Colloid-Light"


def test_a_pack_that_names_nothing_keeps_the_themes_choices(tmp_path: Path) -> None:
    pack = read(make_pack(tmp_path / "colloid", LABEL))
    assert pack.look("dark") == Look(None, None, None)


def test_one_icon_set_may_serve_both_variants(tmp_path: Path) -> None:
    pack = read(
        make_pack(tmp_path / "colloid", {**LABEL, "look": {"icons": "Papirus"}})
    )
    assert pack.look("light").icons == pack.look("dark").icons == "Papirus"


@pytest.mark.parametrize(
    "look",
    [
        "Papirus",
        {"font": 10},
        {"icons": ["Papirus"]},
        {"icons": {"dark": 3}},
        {"font": "Inter\n10"},
    ],
)
def test_a_malformed_look_is_refused_when_read(tmp_path: Path, look: object) -> None:
    """A bad look would otherwise break every Theme switch, at login too."""
    with pytest.raises(SkinpackError, match="look"):
        read(make_pack(tmp_path / "colloid", {**LABEL, "look": look}))


@pytest.mark.parametrize("name", ["osiris", "Colloid", "a b", "a\nb", "-x", ".hidden"])
def test_a_skin_needs_a_plain_name_that_is_not_osiris(
    tmp_path: Path, name: str
) -> None:
    """The name becomes a theme name and a settings value, and "osiris" is
    Osiris's own look."""
    with pytest.raises(SkinpackError, match="name"):
        read(make_pack(tmp_path / name, LABEL))
