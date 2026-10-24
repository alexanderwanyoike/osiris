"""Share Skins: a skinpack as one file, opened from one, and a person's own deleted."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from osiris.skins.pack import Skinpack, SkinpackError, read

EXTENSION = ".skinpack"


def export(pack: Skinpack, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    shared = folder / f"{pack.name}{EXTENSION}"
    with zipfile.ZipFile(shared, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(pack.root.rglob("*")):
            if path.is_file():
                archive.write(
                    path, PurePosixPath(pack.name, path.relative_to(pack.root))
                )
    return shared


def open_file(shared: Path, mine: Path) -> Skinpack:
    """Unpack a shared Skin among the person's own; refuse anything else."""
    try:
        archive = zipfile.ZipFile(shared)
    except zipfile.BadZipFile:
        raise SkinpackError(f"{shared.name}: not a skinpack") from None
    with archive, tempfile.TemporaryDirectory() as scratch:
        names = archive.namelist()
        tops = {PurePosixPath(name).parts[0] for name in names if name}
        unsafe = [
            name
            for name in names
            if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
        ]
        if len(tops) != 1 or unsafe:
            raise SkinpackError(f"{shared.name}: not one folder of its own")
        archive.extractall(scratch)
        unpacked = Path(scratch) / tops.pop()
        read(unpacked)
        target = mine / unpacked.name
        mine.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(target, ignore_errors=True)
        shutil.move(unpacked, target)
    return read(target)


def delete(pack: Skinpack, mine: Path) -> None:
    if not pack.root.resolve().is_relative_to(mine.resolve()):
        raise SkinpackError(f"{pack.label} ships with Osiris and cannot be deleted")
    shutil.rmtree(pack.root)
