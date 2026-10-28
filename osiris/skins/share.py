"""Share Skins: a skinpack as one file, opened from one, and a person's own deleted."""

from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from osiris.model.author import as_osiris
from osiris.model.names import slug
from osiris.platform.process import CommandRunner
from osiris.skins.library import OSIRIS
from osiris.skins.pack import (
    LABEL_FILE,
    Skinpack,
    SkinpackError,
    read,
    refuse_programs,
)

EXTENSION = ".skinpack"
AGENTS_FILE = "AGENTS.md"


def export(pack: Skinpack, folder: Path) -> Path:
    refuse_programs(pack)
    folder.mkdir(parents=True, exist_ok=True)
    shared = folder / f"{pack.name}{EXTENSION}"
    with zipfile.ZipFile(shared, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(pack.root.rglob("*")):
            relative = path.relative_to(pack.root)
            if path.is_file() and not _kept_back(relative):
                archive.write(path, PurePosixPath(pack.name, relative))
    return shared


def _kept_back(relative: Path) -> bool:
    """The person's history and Osiris's instructions stay with the person."""
    return ".git" in relative.parts or relative == Path(AGENTS_FILE)


def open_file(
    shared: Path, mine: Path, runner: CommandRunner, shipped: Sequence[Path] = ()
) -> Skinpack:
    """Unpack a shared Skin among the person's own; refuse anything else."""
    try:
        archive = zipfile.ZipFile(shared)
    except zipfile.BadZipFile:
        raise SkinpackError(f"{shared.name}: not a skinpack") from None
    with archive:
        names = archive.namelist()
        tops = {PurePosixPath(name).parts[0] for name in names if name}
        unsafe = [
            name
            for name in names
            if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
        ]
        if len(tops) != 1 or unsafe:
            raise SkinpackError(f"{shared.name}: not one folder of its own")
        top = tops.pop()
        name = free_name(mine, top, shipped)
        with _making(mine, name) as made:
            archive.extractall(
                made.parent,
                [name for name in names if ".git" not in PurePosixPath(name).parts],
            )
            if top != name:
                (made.parent / top).rename(made)
            refuse_programs(read(made))
            start_history(made, f"Open {shared.name}", runner)
    return read(mine / name)


@contextmanager
def _making(mine: Path, name: str) -> Iterator[Path]:
    """Where a new Skin of the person's is made: beside their own, so that it
    joins them in one rename once it is whole, and is removed if it fails."""
    mine.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=mine, prefix=".") as scratch:
        made = Path(scratch) / name
        yield made
        made.rename(mine / name)


def delete(pack: Skinpack, mine: Path) -> None:
    if not pack.root.resolve().is_relative_to(mine.resolve()):
        raise SkinpackError(f"{pack.label} ships with Osiris and cannot be deleted")
    shutil.rmtree(pack.root)


AGENTS = Path(__file__).with_name("skin-agents.md")


def free_name(mine: Path, base: str, shipped: Sequence[Path] = ()) -> str:
    """base, or base-2, base-3 and so on, whichever no Skin has."""
    name, number = base, 2
    while name == OSIRIS or any(
        (folder / name).exists() for folder in (mine, *shipped)
    ):
        name, number = f"{base}-{number}", number + 1
    return name


def start_history(skin: Path, message: str, runner: CommandRunner) -> None:
    """Give a person's new Skin its instructions for Osiris and a first commit."""
    (skin / AGENTS_FILE).write_text(AGENTS.read_text().replace("SKIN_NAME", skin.name))
    for step in (("init", "-q"), ("add", "-A")):
        runner.run("git", "-C", str(skin), *step, quiet=True)
    runner.run(
        "git", "-C", str(skin), *as_osiris(), "commit", "-q", "-m", message, quiet=True
    )


def duplicate(
    pack: Skinpack,
    mine: Path,
    runner: CommandRunner,
    label: str | None = None,
    shipped: Sequence[Path] = (),
) -> Skinpack:
    """A person's own copy of a Skin, with history and instructions for Osiris;
    a label makes it a new Skin of that name rather than a copy."""
    base = slug(label) if label else f"{pack.name}-copy"
    name = free_name(mine, base, shipped)
    with _making(mine, name) as copy:
        shutil.copytree(pack.root, copy, ignore=shutil.ignore_patterns(".git"))
        label_of = json.loads((copy / LABEL_FILE).read_text())
        label_of["label"] = label or f"{pack.label} (copy)"
        label_of["style"] = pack.style or pack.name
        (copy / LABEL_FILE).write_text(json.dumps(label_of, indent=2) + "\n")
        start_history(copy, f"Copy {pack.label}", runner)
    return read(mine / name)
