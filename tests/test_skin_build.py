"""Building a Skin: a skinpack compiled in a Theme's colours, as a GTK theme."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from osiris.platform.process import FakeRunner
from osiris.skins.build import Built, build
from osiris.skins.pack import SkinpackError, read

ROSE_PINE = {
    "name": "rose-pine",
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


def make_pack(root: Path) -> Path:
    label = {"label": "Colloid", "author": "a", "version": "1", "licence": "GPL-3.0"}
    files = {
        "skin.json": json.dumps({**label, "source": "https://example.org"}),
        "sass/_palette.scss": "@import 'gaps';\n",
        "files/common/gtk-3.0/assets/check.svg": '<svg fill="{{accent}}"/>',
        "files/dark/cinnamon/assets/panel.svg": '<svg fill="{{surface}}"/>',
        "files/light/cinnamon/assets/panel.svg": '<svg fill="{{background}}"/>',
        "plank/dock-dark.theme": "FillStartColor={{background_plank}}\n",
        "plank/dock-light.theme": "FillStartColor=0;;0;;0;;0\n",
        **{
            f"{folder}/{stem}-{variant}.scss": ""
            for folder, stem in (
                ("gtk-3.0", "gtk"),
                ("gtk-4.0", "gtk"),
                ("cinnamon", "cinnamon"),
                ("libadwaita", "libadwaita"),
            )
            for variant in ("light", "dark")
        },
    }
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)
    return root


def build_rose_pine(tmp_path: Path, runner: FakeRunner) -> Built:
    pack = read(make_pack(tmp_path / "colloid"))
    return build(pack, ROSE_PINE, tmp_path / "themes", tmp_path / "work", runner)


def test_each_surface_is_compiled_for_the_themes_variant(tmp_path: Path) -> None:
    runner = FakeRunner()
    build_rose_pine(tmp_path, runner)
    theme = tmp_path / "themes" / "Osiris-colloid-rose-pine"
    work = tmp_path / "work" / "colloid"
    for entry, out in [
        ("gtk-3.0/gtk-dark.scss", "gtk-3.0/gtk.css"),
        ("gtk-4.0/gtk-dark.scss", "gtk-4.0/gtk.css"),
        ("cinnamon/cinnamon-dark.scss", "cinnamon/cinnamon.css"),
        ("libadwaita/libadwaita-dark.scss", "libadwaita.css"),
    ]:
        assert runner.ran(
            "sassc", "-M", "-t", "expanded", str(work / entry), str(theme / out)
        )


def test_the_sass_reads_the_themes_colours(tmp_path: Path) -> None:
    build_rose_pine(tmp_path, FakeRunner())
    gaps = (tmp_path / "work" / "colloid" / "sass" / "_gaps.scss").read_text()
    assert "$gap-accent: #c4a7e7;" in gaps


def test_pictures_for_every_variant_and_this_one_are_installed_filled(
    tmp_path: Path,
) -> None:
    build_rose_pine(tmp_path, FakeRunner())
    theme = tmp_path / "themes" / "Osiris-colloid-rose-pine"
    check = theme / "gtk-3.0" / "assets" / "check.svg"
    assert check.read_text() == '<svg fill="#c4a7e7"/>'
    panel = theme / "cinnamon" / "assets" / "panel.svg"
    assert panel.read_text() == '<svg fill="#1f1d2e"/>'


def test_the_result_names_the_theme_and_carries_the_dock(tmp_path: Path) -> None:
    built = build_rose_pine(tmp_path, FakeRunner())
    theme = tmp_path / "themes" / "Osiris-colloid-rose-pine"
    assert built.theme == "Osiris-colloid-rose-pine"
    assert built.dock == "FillStartColor=25;;23;;36;;255\n"
    assert built.adwaita == theme / "libadwaita.css"
    assert "GtkTheme=Osiris-colloid-rose-pine" in (theme / "index.theme").read_text()


def test_building_prints_nothing_of_its_own(tmp_path: Path) -> None:
    runner = FakeRunner()
    build_rose_pine(tmp_path, runner)
    assert runner.lines == []


def test_a_pack_with_a_launcher_gets_it_in_the_themes_colours(tmp_path: Path) -> None:
    root = make_pack(tmp_path / "colloid")
    (root / "rofi").mkdir()
    (root / "rofi" / "launcher.rasi").write_text("* { accent: {{accent}}; }")
    built = build(
        read(root), ROSE_PINE, tmp_path / "themes", tmp_path / "work", FakeRunner()
    )
    assert built.launcher == "* { accent: #c4a7e7; }"


def test_a_pack_without_a_launcher_leaves_osiris_own(tmp_path: Path) -> None:
    assert build_rose_pine(tmp_path, FakeRunner()).launcher is None


def make_gtk_only_pack(root: Path) -> Path:
    label = {"label": "elementary", "author": "a", "version": "1", "licence": "GPL-3.0"}
    (root / "sass").mkdir(parents=True)
    (root / "skin.json").write_text(json.dumps({**label, "source": "s"}))
    for variant in ("light", "dark"):
        (root / "gtk-3.0").mkdir(exist_ok=True)
        (root / "gtk-3.0" / f"gtk-{variant}.scss").write_text("")
    return root


def test_a_pack_may_leave_the_panel_dock_and_libadwaita_to_osiris(
    tmp_path: Path,
) -> None:
    runner = FakeRunner()
    pack = read(make_gtk_only_pack(tmp_path / "elementary"))
    built = build(pack, ROSE_PINE, tmp_path / "themes", tmp_path / "work", runner)
    assert runner.count("sassc") == 1
    assert built.cinnamon is False
    assert built.dock is None
    assert built.adwaita is None


def test_a_full_pack_brings_its_own_panel(tmp_path: Path) -> None:
    assert build_rose_pine(tmp_path, FakeRunner()).cinnamon is True


def test_a_picture_needs_only_the_gtk3_sheet(tmp_path: Path) -> None:
    """Pictures are drawn for every Skin in the Theme, so they build no more
    than they show."""
    runner = FakeRunner()
    pack = read(make_pack(tmp_path / "colloid"))
    build(
        pack,
        ROSE_PINE,
        tmp_path / "themes",
        tmp_path / "work",
        runner,
        only=("gtk-3.0",),
    )
    assert runner.count("sassc") == 1
    assert runner.ran(
        "sassc",
        "-M",
        "-t",
        "expanded",
        str(tmp_path / "work" / "colloid" / "gtk-3.0" / "gtk-dark.scss"),
    )


def test_a_skins_css_files_take_gaps_like_its_pictures(tmp_path: Path) -> None:
    """An imported theme is plain CSS; converting it puts gaps straight into it."""
    root = make_gtk_only_pack(tmp_path / "neon")
    (root / "gtk-3.0" / "gtk-dark.scss").unlink()
    sheet = root / "files" / "dark" / "gtk-3.0" / "gtk.css"
    sheet.parent.mkdir(parents=True)
    sheet.write_text("window { background: {{background}}; }")
    build(read(root), ROSE_PINE, tmp_path / "themes", tmp_path / "work", FakeRunner())
    built = tmp_path / "themes" / "Osiris-neon-rose-pine" / "gtk-3.0" / "gtk.css"
    assert built.read_text() == "window { background: #191724; }"


def test_a_pack_without_sass_still_builds(tmp_path: Path) -> None:
    root = make_gtk_only_pack(tmp_path / "neon")
    shutil.rmtree(root / "sass")
    built = build(
        read(root), ROSE_PINE, tmp_path / "themes", tmp_path / "work", FakeRunner()
    )
    assert built.theme == "Osiris-neon-rose-pine"


def test_a_skin_holding_a_program_is_not_built(tmp_path: Path) -> None:
    root = make_pack(tmp_path / "colloid")
    (root / "follow.py").write_text("print()")
    runner = FakeRunner()
    with pytest.raises(SkinpackError, match=r"follow\.py is not part of a Skin"):
        build(read(root), ROSE_PINE, tmp_path / "themes", tmp_path / "work", runner)
    assert runner.count("sassc") == 0


@pytest.mark.parametrize("picture", ["check.svg", "gtk.css"])
def test_a_picture_that_is_not_utf8_is_a_skinpack_error(
    tmp_path: Path, picture: str
) -> None:
    """Any other error escapes the fallback to Osiris's own look, and every
    Theme switch fails."""
    root = make_pack(tmp_path / "colloid")
    (root / "files" / "common" / "gtk-3.0" / picture).write_bytes(b"\xff\xfe<svg/>")
    with pytest.raises(SkinpackError, match=picture):
        build(
            read(root), ROSE_PINE, tmp_path / "themes", tmp_path / "work", FakeRunner()
        )


def test_a_theme_whose_name_is_not_a_slug_is_not_built(tmp_path: Path) -> None:
    """The name is joined into the theme folder that is removed first."""
    outside = tmp_path / "themes" / "Osiris-colloid-x" / "keep"
    outside.mkdir(parents=True)
    theme = {**ROSE_PINE, "name": "x/../../themes/Osiris-colloid-x"}
    with pytest.raises(SkinpackError, match="name"):
        build(
            read(make_pack(tmp_path / "colloid")),
            theme,
            tmp_path / "themes",
            tmp_path / "work",
            FakeRunner(),
        )
    assert outside.is_dir()


def test_a_pack_without_a_gtk3_sheet_for_the_variant_is_refused(
    tmp_path: Path,
) -> None:
    """Without it the theme is named but draws nothing of the Skin."""
    root = make_gtk_only_pack(tmp_path / "elementary")
    (root / "gtk-3.0" / "gtk-dark.scss").unlink()
    with pytest.raises(SkinpackError, match=r"gtk-3\.0"):
        build(
            read(root), ROSE_PINE, tmp_path / "themes", tmp_path / "work", FakeRunner()
        )
