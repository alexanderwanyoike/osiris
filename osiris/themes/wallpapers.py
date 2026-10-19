"""Moving wallpapers as packages a theme can name and an agent can write.

A package is a folder named after the wallpaper, holding three files:

    wallpaper.json   {"name": ..., "label": ..., "loop": seconds per turn}
    shader.glsl      vec3 wallpaper(vec2 uv): the motion, drawn on the GPU
    still.py         still(theme, size, phase=None): the still, drawn by Pillow

Both halves are coloured from the theme, and are the same picture: the still
is what previews, the boot screen and a machine without a GPU show, and the
shader at phase 0 must match it. The drift@osiris extension compiles the
shader after its prelude; ``source`` assembles the same program for checking.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from osiris.model.names import slug
from osiris.platform import FileSystem
from osiris.platform.process import CommandRunner

#: Where the shipped packages are installed; a user's own live in USER.
SYSTEM = Path("/usr/share/osiris/themes/wallpapers")
USER = Path(".local/share/osiris/wallpapers")

#: The body of the extension's fragment snippet. Cogl compiles GLSL 1.20.
CODE = "cogl_color_out = vec4(wallpaper(cogl_tex_coord_in[0].xy), 1.0);"

# What Cogl declares around a snippet, as far as a shader can see it.
_HEADER = (
    "#version 120\n"
    "varying vec4 cogl_tex_coord_in[1];\n"
    "#define cogl_color_out gl_FragColor\n"
)

_ERROR = re.compile(r"^ERROR: \d+:(\d+): (.*)$")


class WallpaperError(ValueError):
    """A package that cannot be used, and why."""


@dataclass(frozen=True)
class Wallpaper:
    name: str
    label: str
    loop: float
    directory: Path

    @property
    def shader(self) -> Path:
        return self.directory / "shader.glsl"

    @property
    def still(self) -> Path:
        return self.directory / "still.py"


def load(directory: Path) -> Wallpaper:
    try:
        meta = json.loads((directory / "wallpaper.json").read_text())
    except (OSError, ValueError) as error:
        raise WallpaperError(f"{directory}/wallpaper.json: {error}") from error
    if not isinstance(meta, dict):
        raise WallpaperError(f"{directory}/wallpaper.json: not an object")
    # Themes name a wallpaper by its folder, so the two cannot disagree.
    if meta.get("name") != directory.name:
        raise WallpaperError(
            f"{directory}: name {meta.get('name')!r} is not the folder's name"
        )
    loop = meta.get("loop")
    if isinstance(loop, bool) or not isinstance(loop, int | float) or loop <= 0:
        raise WallpaperError(f"{directory}: loop must be a positive number of seconds")
    wallpaper = Wallpaper(
        directory.name, str(meta.get("label") or directory.name), float(loop), directory
    )
    for part in (wallpaper.shader, wallpaper.still):
        if not part.is_file():
            raise WallpaperError(f"{directory}: missing {part.name}")
    return wallpaper


def discover(
    directories: Sequence[Path],
) -> tuple[dict[str, Wallpaper], list[tuple[Path, str]]]:
    """Every usable package, earlier directories winning, and the rest's faults.

    The user's own folder goes first, so a package there replaces a shipped one
    of the same name.
    """
    found: dict[str, Wallpaper] = {}
    problems: list[tuple[Path, str]] = []
    for root in directories:
        if not root.is_dir():
            continue
        for directory in sorted(p for p in root.iterdir() if p.is_dir()):
            if directory.name in found:
                continue
            try:
                found[directory.name] = load(directory)
            except WallpaperError as error:
                problems.append((directory, str(error)))
    return found, problems


def source(prelude: str, shader: str) -> str:
    """The whole program as Cogl compiles it: prelude, shader, then CODE."""
    return (
        f"{_HEADER}{prelude.rstrip()}\n{shader.rstrip()}\n"
        f"void main() {{\n    {CODE}\n}}\n"
    )


def check(wallpaper: Wallpaper, prelude: str, runner: CommandRunner) -> str | None:
    """Why the package's shader would not compile, or None; see check_shader."""
    return check_shader(wallpaper.shader.read_text(), prelude, runner, wallpaper.name)


def check_shader(
    shader: str, prelude: str, runner: CommandRunner, name: str
) -> str | None:
    """Why the shader would not compile, by its own line numbers, or None.

    glslangValidator is the reference compiler; without it the shader is
    assumed good, and the extension's own fallback is what remains.
    """
    program = source(prelude, shader)
    lines = shader.splitlines()
    first = program.splitlines().index(lines[0]) + 1 if lines else 0
    count = len(lines)
    handle, path = tempfile.mkstemp(suffix=".frag")
    try:
        with os.fdopen(handle, "w") as fh:
            fh.write(program)
        try:
            result = runner.run("glslangValidator", path, check=False, quiet=True)
        except OSError:
            return None
    finally:
        Path(path).unlink()
    if result.ok:
        return None
    reasons = []
    for line in result.stdout.splitlines():
        match = _ERROR.match(line.strip())
        if not match:
            continue
        number, message = int(match.group(1)), match.group(2)
        if first <= number < first + count:
            where = f"{name}/shader.glsl:{number - first + 1}"
            reasons.append(f"{where}: {message}")
        else:
            reasons.append(f"line {number} of the program: {message}")
    return "\n".join(reasons) or result.stdout.strip()


#: The still beside every wallpaper the Harness writes. It is Osiris's, not the
#: model's: still.py runs at every login, and the model writes only GLSL. It
#: cannot match the shader, so previews show a glow in the theme's colours.
STILL = """\
\"\"\"The still for a wallpaper the Harness wrote: Osiris's own glow.\"\"\"
import wallpaper


def still(theme, size, phase=None):
    return wallpaper.compose(theme, size, style="aurora", logo=False, phase=phase)
"""

#: Seconds a wallpaper the Harness writes takes to come round.
LOOP = 60


class UserWallpapers:
    """The person's own wallpaper packages, in ``folder``."""

    def __init__(
        self, files: FileSystem, runner: CommandRunner, folder: Path, prelude: str
    ) -> None:
        self._files = files
        self._runner = runner
        self._folder = folder
        self._prelude = prelude

    def write(self, label: str, shader: str) -> str:
        """Keep a shader as a package, once it compiles. Returns its name."""
        name = slug(label)
        package = self._folder / name
        if self._files.exists(package):
            raise WallpaperError(
                f"There is already a wallpaper called {label}; choose another label"
            )
        problem = check_shader(shader, self._prelude, self._runner, name)
        if problem is not None:
            raise WallpaperError(problem)
        meta = {"name": name, "label": label, "loop": LOOP}
        self._files.write(package / "wallpaper.json", json.dumps(meta) + "\n")
        self._files.write(package / "shader.glsl", shader)
        self._files.write(package / "still.py", STILL)
        return name

    def delete(self, name: str) -> None:
        self._files.remove_tree(self._folder / name)
