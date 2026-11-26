"""Where the Harness's Skin tools act: a port onto the Theme engine's Skins.

The real store is the engine in shell/themes, adapted in apps/harness; this
module holds the contract and an in-memory stand-in for tests.
"""

from __future__ import annotations

from typing import Protocol

from osiris.skins.pack import SkinpackError


class SkinStore(Protocol):
    def skins(self) -> list[dict[str, object]]:
        """Each Skin's name and label, whether it is the person's own and worn."""
        ...

    def worn(self) -> str: ...

    def check(self, name: str) -> list[str]:
        """Why the Skin would not be worn: not data only, or not compiling."""
        ...

    def wear(self, name: str) -> None: ...


class FakeSkinStore:
    def __init__(
        self,
        problems: dict[str, list[str]] | None = None,
        worn: str = "osiris",
    ) -> None:
        self.labels = {"osiris": "Osiris", "colloid": "Colloid"}
        self.mine: set[str] = set()
        self.problems = problems or {}
        self.current = worn

    def skins(self) -> list[dict[str, object]]:
        return [
            {"name": name, "label": label, "mine": name in self.mine,
             "worn": name == self.current}
            for name, label in self.labels.items()
        ]  # fmt: skip

    def worn(self) -> str:
        return self.current

    def check(self, name: str) -> list[str]:
        return list(self.problems.get(name, []))

    def wear(self, name: str) -> None:
        if name not in self.labels:
            raise SkinpackError(f"no Skin called {name}")
        self.current = name
