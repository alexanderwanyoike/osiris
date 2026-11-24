"""Fixed colours in a person's Skin: colours written in rather than taken from
the Theme, which stay the same whatever Theme is worn."""

from __future__ import annotations

import json
from pathlib import Path

from osiris.platform.process import SubprocessRunner
from osiris.skins.colours import fixed_colours, originals
from osiris.skins.pack import read
from osiris.skins.share import commit


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


def make_skin(root: Path, style: str, sheet: str) -> Path:
    label = {"label": root.name, "author": "a", "version": "1", "licence": "MIT"}
    write(root / "skin.json", json.dumps({**label, "source": "", "style": style}))
    write(root / "gtk-3.0" / "gtk-dark.scss", sheet)
    return root


def named(root: Path, folders: list[Path], scratch: Path) -> list[str]:
    found = originals(read(root), folders, SubprocessRunner(), scratch)
    return fixed_colours(root, found)


def test_colours_the_skin_had_when_it_was_made_are_not_named(tmp_path: Path) -> None:
    """Its style may since have been deleted, upgraded or never been here."""
    mine = make_skin(tmp_path / "mine" / "sumi", "gone", "a { color: #123456; }")
    commit(mine, "Copy Graphite", SubprocessRunner())
    write(
        mine / "gtk-3.0" / "gtk-dark.scss",
        "a { color: #123456; } b { color: #2f7d4a; }",
    )
    found = named(mine, [tmp_path / "mine"], tmp_path / "scratch")
    assert found == ["gtk-3.0/gtk-dark.scss: #2f7d4a"]


def test_the_skin_its_style_names_is_an_original(tmp_path: Path) -> None:
    make_skin(tmp_path / "shipped" / "graphite", "", "a { color: #123456; }")
    mine = make_skin(tmp_path / "mine" / "sumi", "graphite", "a { color: #123456; }")
    folders = [tmp_path / "mine", tmp_path / "shipped"]
    assert named(mine, folders, tmp_path / "scratch") == []


def test_a_skin_is_not_its_own_original(tmp_path: Path) -> None:
    mine = make_skin(tmp_path / "mine" / "sumi", "sumi", "a { color: #2f7d4a; }")
    found = named(mine, [tmp_path / "mine"], tmp_path / "scratch")
    assert found == ["gtk-3.0/gtk-dark.scss: #2f7d4a"]


def test_a_link_out_of_the_first_commit_leaves_the_style_to_compare(
    tmp_path: Path,
) -> None:
    """The tar filter refuses such a link; the check must still answer."""
    make_skin(tmp_path / "shipped" / "graphite", "", "a { color: #123456; }")
    mine = make_skin(tmp_path / "mine" / "sumi", "graphite", "a { color: #123456; }")
    (mine / "themes").symlink_to("/usr/share/themes")
    commit(mine, "Copy Graphite", SubprocessRunner())
    folders = [tmp_path / "mine", tmp_path / "shipped"]
    assert named(mine, folders, tmp_path / "scratch") == []


def test_one_scratch_folder_serves_two_skins(tmp_path: Path) -> None:
    first = make_skin(tmp_path / "mine" / "a", "", "a { color: #2f7d4a; }")
    commit(first, "Copy", SubprocessRunner())
    second = make_skin(tmp_path / "mine" / "b", "", "a { color: #000001; }")
    commit(second, "Copy", SubprocessRunner())
    write(
        second / "gtk-3.0" / "gtk-dark.scss",
        "a { color: #000001; } b { color: #2f7d4a; }",
    )
    named(first, [], tmp_path / "scratch")
    found = named(second, [], tmp_path / "scratch")
    assert found == ["gtk-3.0/gtk-dark.scss: #2f7d4a"]
