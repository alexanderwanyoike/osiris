"""The blank slate: adw-gtk3 in the Theme's colours, with no look of its own."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from osiris.platform.process import SubprocessRunner
from osiris.skins.build import build
from osiris.skins.pack import read

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("sassc") is None, reason="needs sassc")
@pytest.mark.parametrize(
    ("theme_name", "base"),
    [("rose-pine", "adw-gtk3-dark"), ("rose-pine-dawn", "adw-gtk3")],
)
def test_the_blank_slate_is_adw_gtk3_in_the_themes_colours(
    theme_name: str, base: str, tmp_path: Path
) -> None:
    theme = json.loads((ROOT / "shell" / "themes" / f"{theme_name}.json").read_text())
    colours = theme["colors"]
    built = build(
        read(ROOT / "shell" / "skins" / "blank"),
        theme,
        tmp_path / "themes",
        tmp_path / "work",
        SubprocessRunner(),
    )
    for version in ("gtk-3.0", "gtk-4.0"):
        css = (tmp_path / "themes" / built.theme / version / "gtk.css").read_text()
        assert f'@import url("/usr/share/themes/{base}/{version}/gtk.css")' in css
        named = dict(re.findall(r"@define-color\s+(\w+)\s+([^;]+);", css))
        assert named["accent_bg_color"] == colours["accent"]
        assert named["window_bg_color"] == colours["surface"]
        assert named["window_fg_color"] == colours["foreground"]
        assert named["view_bg_color"] == colours["background"]


def test_the_blank_slate_leaves_the_panel_dock_and_launcher_to_osiris() -> None:
    blank = ROOT / "shell" / "skins" / "blank"
    assert read(blank).label == "Blank"
    for surface in ("cinnamon", "plank", "rofi", "libadwaita"):
        assert not (blank / surface).exists(), surface
