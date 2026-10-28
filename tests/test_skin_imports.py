"""Importing what a person downloaded for their Skins: icon sets, cursor sets,
fonts and GTK themes, from the archives they usually come in."""

from __future__ import annotations

import io
import os
import shutil
import tarfile
import zipfile
from pathlib import Path

import pytest

from osiris.platform.process import CommandError, FakeRunner
from osiris.skins.check import problems
from osiris.skins.imports import (
    UnusableDownload,
    import_gtk_theme,
    install_fonts,
    install_sets,
    unpack,
)


def make_zip(path: Path, files: dict[str, str]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    return path


def make_tar(
    path: Path,
    files: dict[str, str],
    mode: str = "w:gz",
    links: dict[str, str] | None = None,
) -> Path:
    with tarfile.open(path, mode) as archive:
        for name, text in files.items():
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        for name, points_to in (links or {}).items():
            info = tarfile.TarInfo(name)
            info.type, info.linkname = tarfile.SYMTYPE, points_to
            archive.addfile(info)
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


@pytest.mark.parametrize("name", ["hicolor", "default", "locolor", "dark", "Light"])
def test_a_set_named_like_a_fallback_or_a_variant_is_refused(
    tmp_path: Path, name: str
) -> None:
    """Review of #136: a download could replace hicolor, which every set falls
    back to, or default, which names the cursor."""
    kept = tmp_path / "icons" / name
    kept.mkdir(parents=True)
    (kept / "index.theme").write_text("mine")
    download = make_zip(tmp_path / "sets.zip", {f"{name}/index.theme": ICON_INDEX})
    with pytest.raises(UnusableDownload, match=name):
        install_sets(download, tmp_path / "icons")
    assert (kept / "index.theme").read_text() == "mine"


def test_a_set_the_system_already_has_is_refused(tmp_path: Path) -> None:
    """Review of #136: a set in the person's icons hides the system's of the
    same name, which a system update then no longer reaches."""
    system = tmp_path / "usr-icons"
    (system / "Adwaita").mkdir(parents=True)
    download = make_zip(tmp_path / "sets.zip", {"Adwaita/index.theme": ICON_INDEX})
    with pytest.raises(UnusableDownload, match="Adwaita"):
        install_sets(download, tmp_path / "icons", system=[system])
    assert not (tmp_path / "icons" / "Adwaita").exists()


def test_a_failed_import_keeps_the_sets_it_would_have_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review of #136: the old set was removed before the new one was copied,
    so a copy that failed part-way left neither."""
    old = tmp_path / "icons" / "Neon"
    old.mkdir(parents=True)
    (old / "stale.png").write_text("old")
    download = make_zip(
        tmp_path / "neon.zip",
        {"Neon/index.theme": ICON_INDEX, "Neon-cursors/cursors/left_ptr": "Xcur"},
    )
    copy = shutil.copyfile

    def failing(source: Path, target: Path, **kwargs: bool) -> object:
        if Path(source).name == "left_ptr":
            raise OSError("disk full")
        return copy(source, target, **kwargs)

    monkeypatch.setattr(shutil, "copyfile", failing)
    with pytest.raises(OSError, match="disk full"):
        install_sets(download, tmp_path / "icons")
    assert (old / "stale.png").read_text() == "old"
    assert [entry.name for entry in (tmp_path / "icons").iterdir()] == ["Neon"]


def test_a_set_keeps_its_own_links_even_dangling_or_looping(tmp_path: Path) -> None:
    """Review of #136: a dangling link or a loop, common in icon sets, made the
    copy fail."""
    download = make_tar(
        tmp_path / "neon.tar.gz",
        {"Neon/index.theme": ICON_INDEX, "Neon/48x48/apps/folder.png": "png"},
        links={
            "Neon/48x48/apps/alias.png": "folder.png",
            "Neon/48x48/apps/gone.png": "missing.png",
            "Neon/48x48/apps/one.png": "two.png",
            "Neon/48x48/apps/two.png": "one.png",
        },
    )
    install_sets(download, tmp_path / "icons")
    apps = tmp_path / "icons" / "Neon" / "48x48" / "apps"
    assert (apps / "alias.png").readlink() == Path("folder.png")
    assert (apps / "alias.png").read_text() == "png"


def test_only_a_sets_data_is_installed_and_never_executable(tmp_path: Path) -> None:
    """Review of #136: an import copied programs, exec bits, dotfiles, a nested
    git history and links reaching out of the set."""
    download = tmp_path / "neon.tar.gz"
    with tarfile.open(download, "w:gz") as archive:
        for name, mode in [
            ("Neon/index.theme", 0o644),
            ("Neon/48x48/apps/folder.png", 0o755),
            ("Neon/install.sh", 0o755),
            ("Neon/.git/config", 0o644),
            ("Neon/.hidden.png", 0o644),
        ]:
            data = ICON_INDEX.encode()
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), mode
            archive.addfile(info, io.BytesIO(data))
        info = tarfile.TarInfo("Neon/48x48/apps/outside.png")
        info.type, info.linkname = tarfile.SYMTYPE, "../../../Other/x.png"
        archive.addfile(info)
    install_sets(download, tmp_path / "icons")
    neon = tmp_path / "icons" / "Neon"
    installed = sorted(p.relative_to(neon).as_posix() for p in neon.rglob("*"))
    assert installed == ["48x48", "48x48/apps", "48x48/apps/folder.png", "index.theme"]
    assert not os.access(neon / "48x48" / "apps" / "folder.png", os.X_OK)


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


def test_the_resource_forks_a_mac_adds_are_not_fonts(tmp_path: Path) -> None:
    """Review of #136: a zip made on a Mac carries __MACOSX/._Inter.ttf, which
    is not a font and was installed as one."""
    family = make_zip(
        tmp_path / "inter.zip",
        {"Inter/Inter.ttf": "font", "__MACOSX/Inter/._Inter.ttf": "fork"},
    )
    names = install_fonts([family], tmp_path / "fonts")
    assert names == ["Inter.ttf"]
    assert (tmp_path / "fonts" / "Inter.ttf").read_text() == "font"


def test_a_folder_named_like_a_font_is_not_one(tmp_path: Path) -> None:
    """Review of #136: a folder called Inter.ttf broke the whole import."""
    family = make_zip(tmp_path / "inter.zip", {"Inter.ttf/Inter-Regular.ttf": "f"})
    assert install_fonts([family], tmp_path / "fonts") == ["Inter-Regular.ttf"]


def test_fonts_of_the_same_name_are_all_kept(tmp_path: Path) -> None:
    """Review of #136: two families each with a Regular.ttf left only the last."""
    first = make_zip(tmp_path / "one.zip", {"One/Regular.ttf": "one"})
    second = make_zip(tmp_path / "two.zip", {"Two/Regular.ttf": "two"})
    names = install_fonts([first, second], tmp_path / "fonts")
    assert names == ["Regular-2.ttf", "Regular.ttf"]
    assert (tmp_path / "fonts" / "Regular-2.ttf").read_text() == "two"


def test_a_download_with_no_font_in_it_is_refused(tmp_path: Path) -> None:
    notes = tmp_path / "notes.txt"
    notes.write_text("no fonts")
    with pytest.raises(UnusableDownload, match="no font"):
        install_fonts([notes], tmp_path / "fonts")


def test_a_gtk_theme_with_light_and_dark_becomes_a_skin_of_both(tmp_path: Path) -> None:
    download = make_tar(
        tmp_path / "Neon.tar.xz",
        {
            "Neon/gtk-3.0/gtk.css": "window { background: #ffffff; }",
            "Neon/gtk-4.0/gtk.css": "window { background: #ffffff; }",
            "Neon/cinnamon/cinnamon.css": "#panel { background: #eeeeee; }",
            "Neon/xfwm4/themerc": "skipped",
            "Neon-Dark/gtk-3.0/gtk.css": "window { background: #111111; }",
            "Neon-Dark/plank/dock.theme": "[PlankTheme]\n",
        },
        "w:xz",
    )
    skin = import_gtk_theme(download, tmp_path / "mine", FakeRunner())
    assert (skin.name, skin.label) == ("neon", "Neon")
    files = skin.root / "files"
    assert (
        files / "light" / "gtk-3.0" / "gtk.css"
    ).read_text() == "window { background: #ffffff; }"
    assert (files / "light" / "cinnamon" / "cinnamon.css").is_file()
    assert (
        files / "dark" / "gtk-3.0" / "gtk.css"
    ).read_text() == "window { background: #111111; }"
    assert not (files / "light" / "xfwm4").exists()
    assert (skin.root / "plank" / "dock-dark.theme").is_file()


def test_only_a_gtk_themes_data_becomes_the_skin(tmp_path: Path) -> None:
    """Review of #136: an import copied programs, exec bits and dotfiles into
    the person's Skin, which check_skin then refused to wear."""
    download = tmp_path / "plain.tar.gz"
    with tarfile.open(download, "w:gz") as archive:
        for name, mode in [
            ("Plain/gtk-3.0/gtk.css", 0o755),
            ("Plain/gtk-3.0/render.sh", 0o755),
            ("Plain/gtk-3.0/.git/config", 0o644),
            ("Plain/plank/dock.theme", 0o755),
        ]:
            info = tarfile.TarInfo(name)
            info.size, info.mode = 1, mode
            archive.addfile(info, io.BytesIO(b"x"))
    skin = import_gtk_theme(download, tmp_path / "mine", FakeRunner())
    assert problems(skin.root) == []
    assert (skin.root / "files" / "common" / "gtk-3.0" / "gtk.css").is_file()


def test_light_and_dark_are_paired_by_the_themes_own_name(tmp_path: Path) -> None:
    """Review of #136: a theme with colour variants had its light paired with a
    colour's dark."""
    download = make_zip(
        tmp_path / "yaru.zip",
        {
            f"{name}/gtk-3.0/gtk.css": name
            for name in ("Yaru", "Yaru-blue", "Yaru-blue-Dark")
        },
    )
    skin = import_gtk_theme(download, tmp_path / "mine", FakeRunner())
    assert skin.label == "Yaru"
    files = skin.root / "files"
    assert (files / "common" / "gtk-3.0" / "gtk.css").read_text() == "Yaru"
    assert not (files / "dark").exists()


def test_a_dark_variant_is_named_by_its_suffix(tmp_path: Path) -> None:
    """Review of #136: "dark" anywhere in a name made a variant dark."""
    download = make_zip(
        tmp_path / "darkroom.zip",
        {f"{name}/gtk-3.0/gtk.css": name for name in ("Darkroom", "Darkroom-dark")},
    )
    skin = import_gtk_theme(download, tmp_path / "mine", FakeRunner())
    files = skin.root / "files"
    assert (files / "light" / "gtk-3.0" / "gtk.css").read_text() == "Darkroom"
    assert (files / "dark" / "gtk-3.0" / "gtk.css").read_text() == "Darkroom-dark"


def test_an_imported_gtk4_sheet_is_the_skins_libadwaita_sheet(tmp_path: Path) -> None:
    """Review of #136: libadwaita reads only the sheet Osiris installs for it,
    so a theme's GTK 4 sheet left in gtk-4.0 never reached it. Its pictures
    stay where the sheet names them."""
    download = make_zip(
        tmp_path / "plain.zip",
        {
            "Plain/gtk-3.0/gtk.css": "window {}",
            "Plain/gtk-4.0/gtk.css": "headerbar {}",
            "Plain/gtk-4.0/assets/check.png": "png",
        },
    )
    skin = import_gtk_theme(download, tmp_path / "mine", FakeRunner())
    common = skin.root / "files" / "common"
    assert (common / "libadwaita.css").read_text() == "headerbar {}"
    assert not (common / "gtk-4.0" / "gtk.css").exists()
    assert (common / "gtk-4.0" / "assets" / "check.png").is_file()


def test_a_theme_with_one_variant_serves_both(tmp_path: Path) -> None:
    download = make_zip(tmp_path / "plain.zip", {"Plain/gtk-3.0/gtk.css": "window {}"})
    skin = import_gtk_theme(download, tmp_path / "mine", FakeRunner())
    assert (skin.root / "files" / "common" / "gtk-3.0" / "gtk.css").is_file()


def test_an_imported_theme_is_ready_to_be_converted(tmp_path: Path) -> None:
    runner = FakeRunner()
    download = make_zip(tmp_path / "plain.zip", {"Plain/gtk-3.0/gtk.css": "window {}"})
    skin = import_gtk_theme(download, tmp_path / "mine", runner)
    assert "--skin plain" in (skin.root / "AGENTS.md").read_text()
    assert runner.ran("git", "-C", str(skin.root), "init", "-q")
    assert skin.source == "plain.zip"


def test_a_failed_import_leaves_no_half_made_skin(tmp_path: Path) -> None:
    """Review of #136: a Skin whose history could not be started stayed among
    the person's, half made."""
    download = make_zip(tmp_path / "plain.zip", {"Plain/gtk-3.0/gtk.css": "window {}"})
    runner = FakeRunner(results={"git": CommandError(("git",), 128, "no git")})
    with pytest.raises(CommandError):
        import_gtk_theme(download, tmp_path / "mine", runner)
    assert list((tmp_path / "mine").iterdir()) == []


def test_a_download_without_a_gtk_theme_is_refused(tmp_path: Path) -> None:
    download = make_zip(tmp_path / "icons.zip", {"Neon/index.theme": ICON_INDEX})
    with pytest.raises(UnusableDownload, match="no GTK theme"):
        import_gtk_theme(download, tmp_path / "mine", FakeRunner())
