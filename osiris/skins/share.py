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
#: The folder macOS adds to a zip it makes, beside what was zipped.
_MACOS_EXTRAS = "__MACOSX"
#: Unpacked, in bytes: room for the icon sets and fonts a Skin may carry, not
#: for a small file that unpacks to fill the disk.
LARGEST = 1024**3


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
        top, unpacked = _contents(archive, shared.name)
        name = free_name(mine, top, shipped)
        with _making(mine, name) as made:
            archive.extractall(made.parent, unpacked)
            if top != name:
                (made.parent / top).rename(made)
            refuse_programs(read(made))
            _refuse_unbuildable(made)
            start_history(made, f"Open {shared.name}", runner)
    return read(mine / name)


def _contents(archive: zipfile.ZipFile, shown: str) -> tuple[str, list[str]]:
    """The one folder a skinpack holds, and the entries to unpack from it."""
    entries = [
        entry
        for entry in archive.namelist()
        if PurePosixPath(entry).parts[:1] != (_MACOS_EXTRAS,)
    ]
    tops = {PurePosixPath(entry).parts[0] for entry in entries if entry}
    unsafe = [
        entry
        for entry in entries
        if PurePosixPath(entry).is_absolute()
        or ".." in PurePosixPath(entry).parts
        or (len(PurePosixPath(entry).parts) == 1 and not entry.endswith("/"))
    ]
    if len(tops) != 1 or unsafe:
        raise SkinpackError(f"{shown}: not one folder of its own")
    if sum(info.file_size for info in archive.infolist()) > LARGEST:
        raise SkinpackError(f"{shown}: too large to be a Skin")
    kept = [entry for entry in entries if ".git" not in PurePosixPath(entry).parts]
    return tops.pop(), kept


def _refuse_unbuildable(root: Path) -> None:
    """GTK 3 is the one surface every Skin styles, in both variants: from a
    Sass entry, or from compiled sheets in files/."""
    for variant in ("light", "dark"):
        compiled = (
            root / "files" / folder / "gtk-3.0" / "gtk.css"
            for folder in ("common", variant)
        )
        if not (root / "gtk-3.0" / f"gtk-{variant}.scss").is_file() and not any(
            path.is_file() for path in compiled
        ):
            raise SkinpackError(f"{root.name}: no GTK 3 style for {variant} Themes")


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
    commit(skin, message, runner)


#: Signing would ask for the person's key, and their hooks are for their own
#: commits, not Osiris's.
_UNHOOKED = ("-c", "commit.gpgsign=false", "-c", "core.hooksPath=")


def commit(skin: Path, message: str, runner: CommandRunner, check: bool = True) -> None:
    """Commit everything in a person's Skin as Osiris, starting its history if
    it has none."""
    where = str(skin)
    if not (skin / ".git").exists():
        runner.run("git", "-C", where, "init", "-q", quiet=True)
    runner.run("git", "-C", where, "add", "-A", quiet=True)
    runner.run(
        "git", "-C", where, *as_osiris(), *_UNHOOKED, "commit", "-q", "-m", message,
        check=check, quiet=True,
    )  # fmt: skip


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
        label_of["label"] = label or f"{pack.label.removesuffix(' (copy)')} (copy)"
        label_of["style"] = pack.style or pack.name
        (copy / LABEL_FILE).write_text(json.dumps(label_of, indent=2) + "\n")
        start_history(copy, f"Copy {pack.label}", runner)
    return read(mine / name)
