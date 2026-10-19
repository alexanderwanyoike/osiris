"""The person's own moving wallpapers, as the Harness writes them: a shader it
wrote, checked before it is kept, and a still Osiris supplies."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from osiris.platform import FakeFileSystem
from osiris.platform.process import FakeRunner, Result
from osiris.themes.wallpapers import STILL, UserWallpapers, WallpaperError

FOLDER = Path("/home/tester/.local/share/osiris/wallpapers")
SHADER = "vec3 wallpaper(vec2 uv) {\n    return u_accent * uv.y;\n}\n"
PRELUDE = "uniform float u_time;\nuniform vec3 u_accent;\n"


def broken() -> FakeRunner:
    return FakeRunner(
        results={
            "glslangValidator": Result(
                ("glslangValidator",),
                2,
                "ERROR: 0:7: 'floot' : undeclared identifier\n",
            )
        }
    )


def test_a_wallpaper_is_kept_as_a_package_named_after_its_label() -> None:
    files = FakeFileSystem()
    name = UserWallpapers(files, FakeRunner(), FOLDER, PRELUDE).write(
        "Rain on glass", SHADER
    )
    assert name == "rain-on-glass"
    package = FOLDER / name
    assert json.loads(files.read(package / "wallpaper.json")) == {
        "name": "rain-on-glass",
        "label": "Rain on glass",
        "loop": 60,
    }
    assert files.read(package / "shader.glsl") == SHADER
    assert files.read(package / "still.py") == STILL


def test_a_shader_that_does_not_compile_is_refused_and_nothing_kept() -> None:
    files = FakeFileSystem()
    with pytest.raises(WallpaperError, match="undeclared identifier"):
        UserWallpapers(files, broken(), FOLDER, PRELUDE).write("Rain", SHADER)
    assert not files.exists(FOLDER / "rain")


def test_a_label_already_taken_is_refused() -> None:
    files = FakeFileSystem()
    wallpapers = UserWallpapers(files, FakeRunner(), FOLDER, PRELUDE)
    wallpapers.write("Rain", SHADER)
    with pytest.raises(WallpaperError, match="already a wallpaper called Rain"):
        wallpapers.write("Rain", SHADER)


def test_deleting_a_wallpaper_removes_its_package() -> None:
    files = FakeFileSystem()
    wallpapers = UserWallpapers(files, FakeRunner(), FOLDER, PRELUDE)
    name = wallpapers.write("Rain", SHADER)
    wallpapers.delete(name)
    assert not files.exists(FOLDER / name / "shader.glsl")
