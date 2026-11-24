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


def test_a_colour_written_as_numbers_is_named(tmp_path: Path) -> None:
    sheet = "a { color: rgba($gap-foreground, 0.1); background: rgb(47, 125, 74); }"
    write(tmp_path / "mine" / "gtk-3.0" / "gtk-dark.scss", sheet)
    found = fixed_colours(tmp_path / "mine", None)
    assert found == ["gtk-3.0/gtk-dark.scss: rgb(47, 125, 74)"]


def test_a_sheet_full_of_colours_names_a_few_and_counts_the_rest(
    tmp_path: Path,
) -> None:
    sheet = " ".join(f"a{n} {{ color: #00000{n}; }}" for n in range(1, 6))
    write(tmp_path / "mine" / "files" / "dark" / "gtk-3.0" / "gtk.css", sheet)
    assert fixed_colours(tmp_path / "mine", None) == [
        "files/dark/gtk-3.0/gtk.css: #000001, #000002, #000003 and 2 more"
    ]


def test_references_entities_and_selectors_are_not_colours(tmp_path: Path) -> None:
    svg = '<a xlink:href="#abc"/>&#160;&#8212;<g fill="url(\'#face\')" s="url( #bad)"/>'
    write(tmp_path / "mine" / "files" / "a.svg", svg)
    scss = "&#add-color-button { margin: 0; }\n#cafe-box, #beef_row { margin: 0; }\n"
    write(tmp_path / "mine" / "sass" / "_rows.scss", scss)
    assert fixed_colours(tmp_path / "mine", None) == []
