"""Which Skins there are, and which one the person chose."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from osiris.skins.pack import Skinpack, SkinpackError, read

#: Osiris's own look: adw-gtk3 recoloured by the Theme engine, with no skinpack.
OSIRIS = "osiris"


def chosen(choice: Path) -> str:
    try:
        return choice.read_text().strip() or OSIRIS
    except FileNotFoundError:
        return OSIRIS


def choose(choice: Path, name: str) -> None:
    choice.parent.mkdir(parents=True, exist_ok=True)
    choice.write_text(name + "\n")


def available(folders: Sequence[Path]) -> list[Skinpack]:
    """Every skinpack in `folders`; an earlier folder wins a name."""
    found: dict[str, Skinpack] = {}
    for folder in folders:
        if not folder.is_dir():
            continue
        for root in sorted(folder.iterdir()):
            if root.name in found or not root.is_dir():
                continue
            try:
                found[root.name] = read(root)
            except SkinpackError:
                continue
    return list(found.values())


def find(folders: Sequence[Path], name: str) -> Skinpack | None:
    return next((pack for pack in available(folders) if pack.name == name), None)
