"""Building a Skin: a skinpack compiled in a Theme's colours, as a GTK theme."""

from __future__ import annotations

import json
from pathlib import Path

from osiris.platform.process import FakeRunner
from osiris.skins.build import Built, build
from osiris.skins.pack import read

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
