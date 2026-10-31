"""The sampler: a window of widgets drawn off-screen with one GTK 3 theme and
saved as a picture, so every Skin can be shown in the current Theme."""

from __future__ import annotations

import os
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


def test_the_skins_cursor_is_drawn_over_the_window(tmp_path: Path) -> None:
    from osiris.skins.xcursor import Cursor, png

    pointer = tmp_path / "pointer.png"
    pointer.write_bytes(png(Cursor(24, 24, 0, 0, bytes([255, 0, 0, 255]) * 576)))
    plain, pointed = tmp_path / "plain.png", tmp_path / "pointed.png"
    subprocess.run(
        [sys.executable, str(SAMPLER), "Adwaita", str(plain)], check=True, timeout=60
    )
    subprocess.run(
        [
            sys.executable,
            str(SAMPLER),
            "Adwaita",
            str(pointed),
            "--cursor",
            str(pointer),
        ],
        check=True,
        timeout=60,
    )
    assert plain.read_bytes() != pointed.read_bytes()


def test_the_skins_font_is_used(tmp_path: Path) -> None:
    small, large = tmp_path / "small.png", tmp_path / "large.png"
    for font, out in (("Sans 8", small), ("Sans 14", large)):
        subprocess.run(
            [sys.executable, str(SAMPLER), "Adwaita", str(out), "--font", font],
            check=True,
            timeout=60,
        )
    assert small.read_bytes() != large.read_bytes()


def test_an_icon_set_can_be_named(tmp_path: Path) -> None:
    out = tmp_path / "icons.png"
    subprocess.run(
        [sys.executable, str(SAMPLER), "Adwaita", str(out), "--icons", "hicolor"],
        check=True,
        timeout=60,
    )
    assert size_of(out) == (560, 360)


def test_a_theme_built_outside_the_persons_folders_is_found(tmp_path: Path) -> None:
    """The built theme is offered through XDG_DATA_DIRS, so XDG_DATA_HOME
    can stay the person's (#133 review)."""
    from osiris.skins.pictures import sampler_env

    sheet = tmp_path / "themes" / "Probe" / "gtk-3.0" / "gtk.css"
    sheet.parent.mkdir(parents=True)
    sheet.write_text(".background { background: #ff0000; }")
    plain, built = tmp_path / "plain.png", tmp_path / "built.png"
    subprocess.run(
        [sys.executable, str(SAMPLER), "Adwaita", str(plain)], check=True, timeout=60
    )
    subprocess.run(
        [sys.executable, str(SAMPLER), "Probe", str(built)],
        env=sampler_env(os.environ, tmp_path),
        check=True,
        timeout=60,
    )
    assert plain.read_bytes() != built.read_bytes()
