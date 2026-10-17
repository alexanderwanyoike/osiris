"""Moving wallpapers as packages: a shader, a still generator, a description."""

import json
from pathlib import Path

import pytest

from osiris.platform.process import FakeRunner, Result
from osiris.themes.wallpapers import (
    CODE,
    WallpaperError,
    check,
    discover,
    load,
    source,
)

SHADER = "vec3 wallpaper(vec2 uv) {\n    return vec3(uv, 0.0);\n}\n"
PRELUDE = "uniform float u_time;\nuniform vec2 u_size;\n"


def make(
    root: Path,
    name: str,
    label: str = "Glow",
    loop: float = 60,
    files: tuple[str, ...] = ("shader.glsl", "still.py"),
) -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "wallpaper.json").write_text(
        json.dumps({"name": name, "label": label, "loop": loop})
    )
    for file in files:
        (directory / file).write_text(SHADER if file.endswith(".glsl") else "")
    return directory


def test_a_package_describes_itself(tmp_path: Path) -> None:
    wallpaper = load(make(tmp_path, "glow"))
    assert (wallpaper.name, wallpaper.label, wallpaper.loop) == ("glow", "Glow", 60)
    assert wallpaper.shader == tmp_path / "glow" / "shader.glsl"
    assert wallpaper.still == tmp_path / "glow" / "still.py"


@pytest.mark.parametrize("missing", ["shader.glsl", "still.py"])
def test_a_package_needs_both_halves(tmp_path: Path, missing: str) -> None:
    files = tuple(f for f in ("shader.glsl", "still.py") if f != missing)
    with pytest.raises(WallpaperError, match=missing):
        load(make(tmp_path, "glow", files=files))


def test_a_package_is_named_after_its_folder(tmp_path: Path) -> None:
    directory = make(tmp_path, "glow")
    (directory / "wallpaper.json").write_text(
        json.dumps({"name": "other", "label": "Glow", "loop": 60})
    )
    with pytest.raises(WallpaperError, match="folder"):
        load(directory)


@pytest.mark.parametrize("loop", [0, -5, "slow"])
def test_a_loop_is_a_positive_number_of_seconds(tmp_path: Path, loop: object) -> None:
    with pytest.raises(WallpaperError, match="loop"):
        load(make(tmp_path, "glow", loop=loop))  # type: ignore[arg-type]


def test_a_broken_description_is_an_error_not_a_crash(tmp_path: Path) -> None:
    directory = make(tmp_path, "glow")
    (directory / "wallpaper.json").write_text("{not json")
    with pytest.raises(WallpaperError, match=r"wallpaper\.json"):
        load(directory)


def test_the_users_own_win_over_the_shipped_ones(tmp_path: Path) -> None:
    mine, shipped = tmp_path / "mine", tmp_path / "shipped"
    make(mine, "wave", label="My wave")
    make(shipped, "wave", label="Wave")
    make(shipped, "dots", label="Dots")
    found, problems = discover([mine, shipped])
    assert found["wave"].label == "My wave"
    assert set(found) == {"wave", "dots"}
    assert problems == []


def test_a_broken_package_is_reported_and_left_out(tmp_path: Path) -> None:
    make(tmp_path, "good")
    make(tmp_path, "bad", files=("still.py",))
    found, problems = discover([tmp_path, tmp_path / "absent"])
    assert set(found) == {"good"}
    assert [(path.name, "shader.glsl" in reason) for path, reason in problems] == [
        ("bad", True)
    ]


def test_the_program_is_what_cogl_compiles() -> None:
    program = source(PRELUDE, SHADER)
    assert program.startswith("#version 120\n")
    assert program.index(PRELUDE) < program.index(SHADER) < program.index(CODE)
    assert "void main()" in program


def test_a_clean_shader_passes(tmp_path: Path) -> None:
    assert check(load(make(tmp_path, "glow")), PRELUDE, FakeRunner()) is None


def test_errors_point_at_the_wallpapers_own_lines(tmp_path: Path) -> None:
    wallpaper = load(make(tmp_path, "glow"))
    program = source(PRELUDE, SHADER).splitlines()
    line = program.index("    return vec3(uv, 0.0);") + 1
    runner = FakeRunner(
        results={
            "glslangValidator": Result(
                ("glslangValidator",),
                2,
                f"/tmp/x.frag\nERROR: 0:{line}: 'floot' : undeclared identifier\n"
                "ERROR: 1 compilation errors.  No code generated.\n",
            )
        }
    )
    assert check(wallpaper, PRELUDE, runner) == (
        "glow/shader.glsl:2: 'floot' : undeclared identifier"
    )


def test_without_a_validator_the_shader_is_given_the_benefit(tmp_path: Path) -> None:
    runner = FakeRunner(results={"glslangValidator": FileNotFoundError()})
    assert check(load(make(tmp_path, "glow")), PRELUDE, runner) is None
