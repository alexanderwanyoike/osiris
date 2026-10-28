"""Edit a person's Skin: its name, the style it is built on, and its look."""

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from osiris.model.author import as_osiris
from osiris.platform.process import CommandRunner
from osiris.skins.check import DATA_NAMES
from osiris.skins.imports import copy_data
from osiris.skins.pack import LABEL_FIELDS, LABEL_FILE, Skinpack, read

#: What stays the person's when a Skin takes another style.
_KEPT = {LABEL_FILE, "AGENTS.md", ".git"}
#: What a style is made of; see osiris.skins.build.
_LAYOUT = (
    "sass",
    "gtk-3.0",
    "gtk-4.0",
    "cinnamon",
    "libadwaita",
    "files",
    "plank",
    "rofi",
)


@dataclass(frozen=True)
class Edit:
    label: str
    #: The Skin whose style to take, or None to keep the current one.
    style: Skinpack | None
    #: None leaves each to the Theme.
    icons: str | None
    cursor: str | None
    font: str | None


def save(pack: Skinpack, edit: Edit, runner: CommandRunner) -> Skinpack:
    label = json.loads((pack.root / LABEL_FILE).read_text())
    style = edit.style
    if style is not None and style.root.resolve() != pack.root.resolve():
        _take_style(pack, style)
        label.update({field: getattr(style, field) for field in LABEL_FIELDS})
        label["style"] = style.name
    label["label"] = edit.label
    look = _look(label.get("look", {}), edit)
    if look:
        label["look"] = look
    else:
        label.pop("look", None)
    (pack.root / LABEL_FILE).write_text(json.dumps(label, indent=2) + "\n")
    _commit(pack.root, f"Edit {edit.label}", runner)
    return read(pack.root)


def _look(before: Mapping[str, Any], edit: Edit) -> dict[str, Any]:
    icons: Any = edit.icons
    kept = before.get("icons")
    # The editor shows one variant's icons; choosing that same set again keeps
    # the light and dark pair it came from.
    if isinstance(kept, Mapping) and icons in kept.values():
        icons = dict(kept)
    chosen = {"icons": icons, "cursor": edit.cursor, "font": edit.font}
    return {key: value for key, value in chosen.items() if value}


def _commit(root: Path, message: str, runner: CommandRunner) -> None:
    where = str(root)
    if not (root / ".git").exists():
        runner.run("git", "-C", where, "init", "-q", quiet=True)
    runner.run("git", "-C", where, "add", "-A", quiet=True)
    runner.run(
        "git", "-C", where, *as_osiris(), "commit", "-q", "-m", message,
        check=False, quiet=True,
    )  # fmt: skip


def _is_credit(entry: Path) -> bool:
    return (
        entry.name not in _KEPT
        and entry.is_file()
        and not entry.is_symlink()
        and (entry.name in DATA_NAMES or entry.suffix.lower() in {".md", ".txt"})
    )


def _take_style(pack: Skinpack, style: Skinpack) -> None:
    """Copy the style in first, and remove the old one only once that worked."""
    with tempfile.TemporaryDirectory(dir=pack.root.parent) as scratch:
        staged = Path(scratch) / "style"
        staged.mkdir()
        for folder in _LAYOUT:
            if (style.root / folder).is_dir():
                copy_data(style.root / folder, staged / folder)
        for entry in style.root.iterdir():
            if _is_credit(entry):
                shutil.copyfile(entry, staged / entry.name)
        for entry in pack.root.iterdir():
            if entry.name in _KEPT:
                continue
            if entry.is_symlink() or not entry.is_dir():
                entry.unlink()
            else:
                shutil.rmtree(entry)
        for entry in staged.iterdir():
            entry.rename(pack.root / entry.name)
