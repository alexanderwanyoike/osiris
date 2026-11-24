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
    found = fixed_colours(tmp_path / "mine", [tmp_path / "graphite"])
    assert found == ["gtk-3.0/gtk-dark.scss: #2f7d4a"]


def test_colours_the_original_skin_has_are_part_of_its_look(tmp_path: Path) -> None:
    buttons = "close { background-color: #ED5F5D; }\n"
    write(tmp_path / "mine" / "sass" / "_buttons.scss", buttons)
    write(tmp_path / "graphite" / "sass" / "_colors.scss", "$red: #ed5f5d;\n")
    assert fixed_colours(tmp_path / "mine", [tmp_path / "graphite"]) == []


def test_a_picture_pointing_at_its_own_parts_has_no_colour(tmp_path: Path) -> None:
    write(tmp_path / "mine" / "files" / "a.svg", '<rect fill="url(#fade)"/>')
    assert fixed_colours(tmp_path / "mine", []) == []


def test_a_colour_written_as_numbers_is_named(tmp_path: Path) -> None:
    sheet = "a { color: rgba($gap-foreground, 0.1); background: rgb(47, 125, 74); }"
    write(tmp_path / "mine" / "gtk-3.0" / "gtk-dark.scss", sheet)
    found = fixed_colours(tmp_path / "mine", [])
    assert found == ["gtk-3.0/gtk-dark.scss: rgb(47, 125, 74)"]


def test_a_sheet_full_of_colours_names_a_few_and_counts_the_rest(
    tmp_path: Path,
) -> None:
    sheet = " ".join(f"a{n} {{ color: #00000{n}; }}" for n in range(1, 6))
    write(tmp_path / "mine" / "files" / "dark" / "gtk-3.0" / "gtk.css", sheet)
    assert fixed_colours(tmp_path / "mine", []) == [
        "files/dark/gtk-3.0/gtk.css: #000001, #000002, #000003 and 2 more"
    ]


def test_references_entities_and_selectors_are_not_colours(tmp_path: Path) -> None:
    svg = '<a xlink:href="#abc"/>&#160;&#8212;<g fill="url(\'#face\')" s="url( #bad)"/>'
    write(tmp_path / "mine" / "files" / "a.svg", svg)
    scss = "&#add-color-button { margin: 0; }\n#cafe-box, #beef_row { margin: 0; }\n"
    write(tmp_path / "mine" / "sass" / "_rows.scss", scss)
    assert fixed_colours(tmp_path / "mine", []) == []


def test_a_colour_the_original_has_counts_however_it_is_written(
    tmp_path: Path,
) -> None:
    write(
        tmp_path / "graphite" / "sass" / "_c.scss", "$a: #fff; $b: rgba(0, 0, 0, 0.2);"
    )
    write(tmp_path / "mine" / "sass" / "_c.scss", "$a: #FFFFFF; $b: rgba(0,0,0,.2);")
    assert fixed_colours(tmp_path / "mine", [tmp_path / "graphite"]) == []


def test_transparent_is_no_colour(tmp_path: Path) -> None:
    write(tmp_path / "mine" / "sass" / "_c.scss", "$a: #0000; $b: rgba(0, 0, 0, 0);")
    assert fixed_colours(tmp_path / "mine", []) == []


def test_only_the_skins_own_files_are_read(tmp_path: Path) -> None:
    """A link can point at nothing, or outside the Skin; neither is the Skin's."""
    write(tmp_path / "outside.css", "a { color: #2f7d4a; }")
    sheets = tmp_path / "mine" / "gtk-3.0"
    sheets.mkdir(parents=True)
    (sheets / "gtk.css").symlink_to(tmp_path / "outside.css")
    (sheets / "gone.css").symlink_to(tmp_path / "missing.css")
    (sheets / "folder.css").mkdir()
    assert fixed_colours(tmp_path / "mine", []) == []


def test_numbers_that_are_no_number_are_still_read(tmp_path: Path) -> None:
    write(tmp_path / "mine" / "sass" / "_c.scss", "$a: rgb(1.2.3, 4, 5);")
    assert fixed_colours(tmp_path / "mine", []) == ["sass/_c.scss: rgb(1.2.3, 4, 5)"]


def test_a_skin_full_of_colours_names_ten_sheets_and_counts_the_rest(
    tmp_path: Path,
) -> None:
    for n in range(12):
        write(
            tmp_path / "mine" / "files" / f"{n:02}.svg",
            f'<p fill="#00000{n % 9 + 1}"/>',
        )
    found = fixed_colours(tmp_path / "mine", [])
    assert len(found) == 11
    assert found[-1] == "and 2 more sheets"
