"""Importing what a person downloaded for their Skins: icon sets, cursor sets,
fonts and GTK themes, from the archives they usually come in."""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from osiris.skins.imports import UnusableDownload, unpack


def make_zip(path: Path, files: dict[str, str]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    return path


def make_tar(path: Path, files: dict[str, str], mode: str = "w:gz") -> Path:
    with tarfile.open(path, mode) as archive:
        for name, text in files.items():
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return path


def test_a_zip_is_unpacked(tmp_path: Path) -> None:
    download = make_zip(tmp_path / "icons.zip", {"Neon/index.theme": "[Icon Theme]"})
    unpack(download, tmp_path / "out")
    assert (tmp_path / "out" / "Neon" / "index.theme").is_file()


@pytest.mark.parametrize(
    "suffix,mode", [(".tar.gz", "w:gz"), (".tar.xz", "w:xz"), (".tar.bz2", "w:bz2")]
)
def test_tarballs_are_unpacked(tmp_path: Path, suffix: str, mode: str) -> None:
    download = make_tar(
        tmp_path / f"cursors{suffix}", {"Neon/cursors/left_ptr": "x"}, mode
    )
    unpack(download, tmp_path / "out")
    assert (tmp_path / "out" / "Neon" / "cursors" / "left_ptr").is_file()


def test_a_zip_reaching_outside_is_refused(tmp_path: Path) -> None:
    download = make_zip(tmp_path / "evil.zip", {"../escaped.txt": "x"})
    with pytest.raises(UnusableDownload):
        unpack(download, tmp_path / "out")
    assert not (tmp_path / "escaped.txt").exists()


def test_a_tarball_reaching_outside_is_refused(tmp_path: Path) -> None:
    download = make_tar(tmp_path / "evil.tar.gz", {"../escaped.txt": "x"})
    with pytest.raises(UnusableDownload):
        unpack(download, tmp_path / "out")
    assert not (tmp_path / "escaped.txt").exists()


def test_a_file_that_is_not_an_archive_is_refused(tmp_path: Path) -> None:
    junk = tmp_path / "theme.tar.gz"
    junk.write_text("not an archive")
    with pytest.raises(UnusableDownload):
        unpack(junk, tmp_path / "out")
