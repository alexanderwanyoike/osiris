"""Fixed colours in a person's Skin: colours written in rather than taken from
the Theme, which stay the same whatever Theme is worn."""

from __future__ import annotations

from pathlib import Path

from osiris.skins.colours import fixed_colours


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_a_colour_written_into_a_style_sheet_is_named(tmp_path: Path) -> None:
    sheet = "a { color: $gap-accent; }\nb { background-color: #2f7d4a; }\n"
    write(tmp_path / "mine" / "gtk-3.0" / "gtk-dark.scss", sheet)
    write(tmp_path / "graphite" / "gtk-3.0" / "gtk-dark.scss", "")
    found = fixed_colours(tmp_path / "mine", tmp_path / "graphite")
    assert found == ["gtk-3.0/gtk-dark.scss: #2f7d4a"]


def test_colours_the_original_skin_has_are_part_of_its_look(tmp_path: Path) -> None:
    buttons = "close { background-color: #ED5F5D; }\n"
    write(tmp_path / "mine" / "sass" / "_buttons.scss", buttons)
    write(tmp_path / "graphite" / "sass" / "_colors.scss", "$red: #ed5f5d;\n")
    assert fixed_colours(tmp_path / "mine", tmp_path / "graphite") == []


def test_a_picture_pointing_at_its_own_parts_has_no_colour(tmp_path: Path) -> None:
    write(tmp_path / "mine" / "files" / "a.svg", '<rect fill="url(#fade)"/>')
    assert fixed_colours(tmp_path / "mine", None) == []
