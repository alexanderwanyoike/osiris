"""Import what a person downloaded for their Skins: icon sets, cursor sets,
fonts and GTK themes, from the archives they usually come in."""

from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path, PurePosixPath


class UnusableDownload(ValueError):
    """A download that cannot be imported, and why."""


def unpack(download: Path, into: Path) -> None:
    """Unpack a zip or tar archive, refusing members that reach outside."""
    into.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(download):
        with zipfile.ZipFile(download) as archive:
            for name in archive.namelist():
                parts = PurePosixPath(name).parts
                if PurePosixPath(name).is_absolute() or ".." in parts:
                    raise UnusableDownload(f"{download.name}: {name} reaches outside")
            archive.extractall(into)
        return
    try:
        with tarfile.open(download) as archive:
            archive.extractall(into, filter="data")
    except (tarfile.TarError, OSError) as error:
        raise UnusableDownload(f"{download.name}: {error}") from None
