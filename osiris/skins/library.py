"""Which Skins there are, and which one the person chose."""

from __future__ import annotations

from collections.abc import Callable, Sequence
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


def wear_choice(
    choice: Path, name: str, apply: Callable[[], SkinpackError | None]
) -> None:
    """Choose a Skin and apply it; `apply` returns why the Skin was not worn,
    and then Osiris's own look, which the desktop fell back to, is chosen."""
    choose(choice, name)
    failed = apply()
    if failed is not None:
        choose(choice, OSIRIS)
        raise failed


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


def styles(folders: Sequence[Path], editing: str) -> list[Skinpack]:
    """The Skins a Skin can take its style from: every one but itself."""
    return [pack for pack in available(folders) if pack.name != editing]


#: The author osiris.skins.imports writes for a Skin made from a download.
IMPORTED = "Imported"


def credit(pack: Skinpack) -> str:
    """Who made a Skin, as its card says it."""
    if pack.author == IMPORTED:
        return f"Imported from {pack.source}"
    return f"{pack.author}, {pack.licence}"
