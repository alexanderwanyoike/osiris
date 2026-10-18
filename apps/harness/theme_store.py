"""The real ThemeStore: the theme engine in shell/themes, for the tool server
that acts and the drawer that undoes."""
import os
import sys
from collections.abc import Mapping
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for candidate in (os.path.join(REPO, "shell", "themes"), "/usr/share/osiris/themes"):
    if os.path.isdir(candidate):
        sys.path.insert(0, candidate)
        break

import engine  # noqa: E402


class EngineStore:
    def themes(self) -> list[Mapping[str, Any]]:
        return engine.all_themes()

    def current(self) -> str | None:
        return engine.current()

    def save(self, theme: Mapping[str, Any]) -> None:
        engine.save(dict(theme))

    def apply(self, name: str) -> None:
        engine.apply(name)

    def delete(self, name: str) -> None:
        engine.delete(name)
