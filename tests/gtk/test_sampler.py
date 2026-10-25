"""The sampler: a window of widgets drawn off-screen with one GTK 3 theme and
saved as a picture, so every Skin can be shown in the current Theme."""

from __future__ import annotations

import struct
import subprocess
import sys
from pathlib import Path

SAMPLER = Path(__file__).resolve().parents[2] / "apps" / "appearance" / "sampler.py"


def size_of(png: Path) -> tuple[int, int]:
    width, height = struct.unpack(">II", png.read_bytes()[16:24])
    return width, height


def test_a_theme_is_drawn_to_a_picture(tmp_path: Path) -> None:
    picture = tmp_path / "adwaita.png"
    subprocess.run(
        [sys.executable, str(SAMPLER), "Adwaita", str(picture)], check=True, timeout=60
    )
    assert size_of(picture) == (560, 360)


def test_two_themes_draw_differently(tmp_path: Path) -> None:
    light, dark = tmp_path / "light.png", tmp_path / "dark.png"
    for theme, out in (("Adwaita", light), ("Adwaita:dark", dark)):
        subprocess.run(
            [sys.executable, str(SAMPLER), theme, str(out)], check=True, timeout=60
        )
    assert light.read_bytes() != dark.read_bytes()
