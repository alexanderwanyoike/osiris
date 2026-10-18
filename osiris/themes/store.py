"""Where Themes are kept and applied, as a port.

The real store is the theme engine in shell/themes, which writes into the
person's home and repaints the desktop; nothing that decides what to do with
a Theme should need a desktop to be tested.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ThemeStore(Protocol):
    def themes(self) -> list[Mapping[str, Any]]: ...

    def current(self) -> str | None: ...

    def save(self, theme: Mapping[str, Any]) -> None: ...

    def apply(self, name: str) -> None: ...


class FakeThemeStore:
    def __init__(
        self,
        themes: list[Mapping[str, Any]] | None = None,
        current: str | None = None,
    ) -> None:
        self.themes_kept = list(themes or [])
        self.current_name = current
        self.saved: list[Mapping[str, Any]] = []
        self.applied: list[str] = []

    def themes(self) -> list[Mapping[str, Any]]:
        return self.themes_kept

    def current(self) -> str | None:
        return self.current_name

    def save(self, theme: Mapping[str, Any]) -> None:
        self.saved.append(theme)
        self.themes_kept.append(theme)

    def apply(self, name: str) -> None:
        self.applied.append(name)
        self.current_name = name
