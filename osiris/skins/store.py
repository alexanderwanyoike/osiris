"""Where the Harness's Skin tools act: a port onto the Theme engine's Skins.

The real store is the engine in shell/themes, adapted in apps/harness; this
module holds the contract and an in-memory stand-in for tests.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from osiris.model.names import slug
from osiris.skins.pack import SkinpackError

#: Where the stand-in keeps the person's Skins.
FAKE_SKINS = Path("/home/tester/.local/share/osiris/skins")


class SkinStore(Protocol):
    def skins(self) -> list[dict[str, object]]:
        """Each Skin's name and label, whether it is the person's own and worn."""
        ...

    def worn(self) -> str: ...

    def create(self, label: str, base: str) -> Path:
        """A new Skin of the person's from base; its folder."""
        ...

    def check(self, name: str) -> list[str]:
        """Why the Skin would not be worn: not data only, or not compiling."""
        ...

    def wear(self, name: str) -> None: ...

    def delete(self, name: str) -> None: ...

    def import_gtk_theme(self, path: Path) -> str: ...

    def install_icon_sets(self, path: Path) -> list[str]: ...

    def remove_icon_sets(self, names: Sequence[str]) -> None: ...

    def install_fonts(self, paths: Sequence[Path]) -> list[str]: ...

    def remove_fonts(self, names: Sequence[str]) -> None: ...


class FakeSkinStore:
    def __init__(
        self, problems: dict[str, list[str]] | None = None, worn: str = "osiris"
    ) -> None:
        self.labels = {"osiris": "Osiris", "colloid": "Colloid"}
        self.mine: set[str] = set()
        self.problems = problems or {}
        self.current = worn
        self.icon_sets: list[str] = []
        self.fonts: list[str] = []

    def skins(self) -> list[dict[str, object]]:
        return [
            {"name": name, "label": label, "mine": name in self.mine,
             "worn": name == self.current}
            for name, label in self.labels.items()
        ]  # fmt: skip

    def worn(self) -> str:
        return self.current

    def create(self, label: str, base: str) -> Path:
        if base not in self.labels:
            raise SkinpackError(f"no Skin called {base}")
        name = slug(label)
        self.labels[name] = label
        self.mine.add(name)
        return FAKE_SKINS / name

    def check(self, name: str) -> list[str]:
        return list(self.problems.get(name, []))

    def wear(self, name: str) -> None:
        if name not in self.labels:
            raise SkinpackError(f"no Skin called {name}")
        self.current = name

    def delete(self, name: str) -> None:
        if name not in self.mine:
            raise SkinpackError(f"{name} is not the person's to delete")
        del self.labels[name]
        self.mine.discard(name)

    def import_gtk_theme(self, path: Path) -> str:
        return self.create(path.name.split(".")[0], "colloid").name

    def install_icon_sets(self, path: Path) -> list[str]:
        names = [path.name.split(".")[0]]
        self.icon_sets += names
        return names

    def remove_icon_sets(self, names: Sequence[str]) -> None:
        self.icon_sets = [name for name in self.icon_sets if name not in names]

    def install_fonts(self, paths: Sequence[Path]) -> list[str]:
        names = [path.name for path in paths]
        self.fonts += names
        return names

    def remove_fonts(self, names: Sequence[str]) -> None:
        self.fonts = [name for name in self.fonts if name not in names]
