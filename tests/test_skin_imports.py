"""Importing what a person downloaded for their Skins: icon sets, cursor sets,
fonts and GTK themes, from the archives they usually come in."""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from osiris.skins.imports import UnusableDownload, install_fonts, install_sets, unpack


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


ICON_INDEX = "[Icon Theme]\nName=Neon\nDirectories=48x48/apps\n"


def test_icon_and_cursor_sets_are_installed_wherever_they_sit(tmp_path: Path) -> None:
    download = make_tar(
        tmp_path / "neon.tar.xz",
        {
            "Neon-1.2/Neon/index.theme": ICON_INDEX,
            "Neon-1.2/Neon/48x48/apps/folder.png": "png",
            "Neon-1.2/Neon-cursors/cursors/left_ptr": "Xcur",
            "Neon-1.2/README.md": "read me",
        },
        "w:xz",
    )
    names = install_sets(download, tmp_path / "icons")
    assert names == ["Neon", "Neon-cursors"]
    assert (tmp_path / "icons" / "Neon" / "48x48" / "apps" / "folder.png").is_file()
    assert (tmp_path / "icons" / "Neon-cursors" / "cursors" / "left_ptr").is_file()


def test_a_newer_download_replaces_the_set_of_the_same_name(tmp_path: Path) -> None:
    old = tmp_path / "icons" / "Neon"
    old.mkdir(parents=True)
    (old / "stale.png").write_text("old")
    download = make_zip(tmp_path / "neon.zip", {"Neon/index.theme": ICON_INDEX})
    install_sets(download, tmp_path / "icons")
    assert not (old / "stale.png").exists()


def test_a_download_with_no_set_in_it_is_refused(tmp_path: Path) -> None:
    download = make_zip(tmp_path / "wallpapers.zip", {"pics/beach.png": "png"})
    with pytest.raises(UnusableDownload, match="no icon or cursor set"):
        install_sets(download, tmp_path / "icons")


def test_fonts_are_installed_from_files_and_archives(tmp_path: Path) -> None:
    single = tmp_path / "Inter.ttf"
    single.write_text("font")
    family = make_zip(
        tmp_path / "jetbrains.zip",
        {"fonts/ttf/JetBrainsMono.ttf": "f", "OFL.txt": "licence"},
    )
    names = install_fonts([single, family], tmp_path / "fonts")
    assert names == ["Inter.ttf", "JetBrainsMono.ttf"]
    assert (tmp_path / "fonts" / "JetBrainsMono.ttf").is_file()


def test_a_download_with_no_font_in_it_is_refused(tmp_path: Path) -> None:
    notes = tmp_path / "notes.txt"
    notes.write_text("no fonts")
    with pytest.raises(UnusableDownload, match="no font"):
        install_fonts([notes], tmp_path / "fonts")
