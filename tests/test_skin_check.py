"""A Skin is data only: Osiris refuses to build, open or share one that holds
programs, so nothing in a Skin ever runs."""

from __future__ import annotations

import json
import os
from pathlib import Path

from osiris.skins.check import problems

FIELDS = {
    "label": "Old Forest",
    "author": "a",
    "version": "1",
    "licence": "GPL-3.0",
    "source": "s",
}


def make_skin(root: Path, files: dict[str, str | bytes]) -> Path:
    for path, content in {"skin.json": json.dumps(FIELDS), **files}.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content)
    return root


def test_style_sheets_pictures_and_settings_are_fine(tmp_path: Path) -> None:
    root = make_skin(
        tmp_path / "skin",
        {
            "sass/_palette.scss": "",
            "gtk-3.0/gtk-dark.scss": "",
            "files/common/gtk-3.0/gtk.css": "",
            "files/common/gtk-3.0/assets/check.svg": "<svg/>",
            "files/common/gtk-3.0/assets/check.png": b"\x89PNG",
            "plank/dock-dark.theme": "[PlankTheme]",
            "rofi/launcher.rasi": "* {}",
            "AGENTS.md": "",
            "LICENSE": "GPL",
            "fonts/Inter.ttf": b"font",
        },
    )
    assert problems(root) == []


def test_a_script_is_refused_by_name(tmp_path: Path) -> None:
    root = make_skin(
        tmp_path / "skin", {"follow.py": "print()", "tools/build.sh": "echo"}
    )
    assert problems(root) == [
        "follow.py is not part of a Skin",
        "tools/build.sh is not part of a Skin",
    ]


def test_a_service_or_desktop_entry_is_refused(tmp_path: Path) -> None:
    root = make_skin(tmp_path / "skin", {"old-forest-follow.service": "[Unit]"})
    assert problems(root) == ["old-forest-follow.service is not part of a Skin"]


def test_an_executable_file_is_refused_whatever_its_name(tmp_path: Path) -> None:
    root = make_skin(tmp_path / "skin", {"files/common/gtk.css": "window {}"})
    os.chmod(root / "files/common/gtk.css", 0o755)
    assert problems(root) == ["files/common/gtk.css may not be executable"]


def test_cursors_without_a_suffix_are_fine_if_they_are_cursors(tmp_path: Path) -> None:
    root = make_skin(
        tmp_path / "skin",
        {"icons/Bibata/cursors/left_ptr": b"Xcur rest", "icons/Bibata/index.theme": ""},
    )
    (root / "icons/Bibata/cursors/default").symlink_to("left_ptr")
    assert problems(root) == []


def test_a_program_disguised_as_a_cursor_is_refused(tmp_path: Path) -> None:
    root = make_skin(tmp_path / "skin", {"icons/Bibata/cursors/left_ptr": b"\x7fELF"})
    assert problems(root) == ["icons/Bibata/cursors/left_ptr is not part of a Skin"]


def test_a_link_reaching_outside_the_skin_is_refused(tmp_path: Path) -> None:
    root = make_skin(tmp_path / "skin", {})
    (root / "escape.css").symlink_to("/etc/passwd")
    assert problems(root) == ["escape.css links outside the Skin"]


def test_its_history_is_not_judged(tmp_path: Path) -> None:
    root = make_skin(tmp_path / "skin", {".git/hooks/pre-commit.sample": "#!/bin/sh"})
    assert problems(root) == []
