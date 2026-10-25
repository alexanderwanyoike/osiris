"""The icon sets and cursor sets installed, which the Skin editor offers."""

from __future__ import annotations

from pathlib import Path

from osiris.skins.looks import cursor_themes, icon_themes


def theme(root: Path, name: str, index: str | None, cursors: bool = False) -> None:
    folder = root / name
    folder.mkdir(parents=True)
    if index is not None:
        (folder / "index.theme").write_text(index)
    if cursors:
        (folder / "cursors").mkdir()
        (folder / "cursors" / "left_ptr").write_bytes(b"Xcur")


ICONS = "[Icon Theme]\nName={name}\nDirectories=48x48/apps\n"


def test_icon_sets_are_folders_with_icon_directories(tmp_path: Path) -> None:
    theme(tmp_path, "Papirus", ICONS.format(name="Papirus"))
    theme(tmp_path, "Adwaita", ICONS.format(name="Adwaita"), cursors=True)
    theme(tmp_path, "Bibata", "[Icon Theme]\nName=Bibata\n", cursors=True)
    theme(tmp_path, "junk", None)
    assert icon_themes([tmp_path]) == ["Adwaita", "Papirus"]


def test_hidden_and_fallback_sets_are_not_offered(tmp_path: Path) -> None:
    theme(tmp_path, "hicolor", ICONS.format(name="Hicolor"))
    theme(tmp_path, "Secret", ICONS.format(name="Secret") + "Hidden=true\n")
    theme(tmp_path, "Papirus", ICONS.format(name="Papirus"))
    assert icon_themes([tmp_path]) == ["Papirus"]


def test_cursor_sets_are_folders_with_cursors(tmp_path: Path) -> None:
    theme(tmp_path, "Adwaita", ICONS.format(name="Adwaita"), cursors=True)
    theme(tmp_path, "Bibata", "[Icon Theme]\nName=Bibata\n", cursors=True)
    theme(tmp_path, "Papirus", ICONS.format(name="Papirus"))
    assert cursor_themes([tmp_path]) == ["Adwaita", "Bibata"]


def test_a_set_found_in_two_places_is_offered_once(tmp_path: Path) -> None:
    mine, shipped = tmp_path / "mine", tmp_path / "shipped"
    theme(mine, "Papirus", ICONS.format(name="Papirus"))
    theme(shipped, "Papirus", ICONS.format(name="Papirus"))
    assert icon_themes([mine, shipped]) == ["Papirus"]
