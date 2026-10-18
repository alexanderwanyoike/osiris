"""Runs the Osiris tool server on stdio, over the real theme engine.

The Engine spawns this when the Harness registers it; what the tools do is in
osiris/apps/tool_server.py and osiris/themes/actions.py, where it is tested.
"""
import os
import sys
from collections.abc import Mapping
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for candidate in ("/usr/share/osiris/lib", REPO):
    if os.path.isdir(os.path.join(candidate, "osiris")):
        sys.path.insert(0, candidate)
        break
for candidate in (os.path.join(REPO, "shell", "themes"), "/usr/share/osiris/themes"):
    if os.path.isdir(candidate):
        sys.path.insert(0, candidate)
        break

import engine  # noqa: E402

from osiris.apps.tool_server import server  # noqa: E402


class EngineStore:
    def themes(self) -> list[Mapping[str, Any]]:
        return engine.all_themes()

    def current(self) -> str | None:
        return engine.current()

    def save(self, theme: Mapping[str, Any]) -> None:
        engine.save(dict(theme))

    def apply(self, name: str) -> None:
        engine.apply(name)


if __name__ == "__main__":
    server(EngineStore()).run()
