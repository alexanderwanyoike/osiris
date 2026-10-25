"""Edit a person's Skin: its name, the style it is built on, and its look."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass

from osiris.model.author import as_osiris
from osiris.platform.process import CommandRunner
from osiris.skins.pack import LABEL_FIELDS, LABEL_FILE, Skinpack, read

#: What stays the person's when a Skin takes another style.
_KEPT = {LABEL_FILE, "AGENTS.md", ".git"}


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
    if edit.style is not None and edit.style.name != pack.style:
        _take_style(pack, edit.style)
        label.update({field: getattr(edit.style, field) for field in LABEL_FIELDS})
        label["style"] = edit.style.style or edit.style.name
    label["label"] = edit.label
    look = {
        key: value
        for key, value in (
            ("icons", edit.icons),
            ("cursor", edit.cursor),
            ("font", edit.font),
        )
        if value
    }
    if look:
        label["look"] = look
    else:
        label.pop("look", None)
    (pack.root / LABEL_FILE).write_text(json.dumps(label, indent=2) + "\n")
    root = str(pack.root)
    runner.run("git", "-C", root, "add", "-A", quiet=True)
    runner.run(
        "git",
        "-C",
        root,
        *as_osiris(),
        "commit",
        "-q",
        "-m",
        f"Edit {edit.label}",
        check=False,
        quiet=True,
    )
    return read(pack.root)


def _take_style(pack: Skinpack, style: Skinpack) -> None:
    for entry in pack.root.iterdir():
        if entry.name in _KEPT:
            continue
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    for entry in style.root.iterdir():
        if entry.name in _KEPT:
            continue
        if entry.is_dir():
            shutil.copytree(entry, pack.root / entry.name)
        else:
            shutil.copy(entry, pack.root / entry.name)
