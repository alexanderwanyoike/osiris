"""Finding and rendering the files under this package.

Resources are read through `importlib.resources`, not by building a path
relative to `__file__`. The difference matters once the package is installed:
`__file__` points into site-packages at best and into a zip at worst, while the
resources API works in both and in a source checkout.

Rendering is explicit named substitution, not f-strings. A GRUB theme and a
gschema override are both full of braces that mean something to their own
format and nothing to Python, and `str.format` on such a document either throws
or silently mangles it.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from importlib.resources.abc import Traversable

_PLACEHOLDER = re.compile(r"@([A-Z][A-Z0-9_]*)@")

PACKAGE = "osiris.resources"


class MissingResource(FileNotFoundError):
    """A resource was asked for that is not packaged."""


class MissingPlaceholder(KeyError):
    """A template placeholder had no value supplied."""


@dataclass(frozen=True)
class Resources:
    """Read-only access to the packaged configuration files."""

    package: str = PACKAGE

    def _entry(self, name: str) -> Traversable:
        entry: Traversable = resources.files(self.package)
        for part in name.split("/"):
            entry = entry / part
        return entry

    def read(self, name: str) -> str:
        """The contents of a packaged file, e.g. "shell/zshrc"."""
        entry = self._entry(name)
        if not entry.is_file():
            raise MissingResource(f"{self.package}/{name}")
        return entry.read_text(encoding="utf-8")

    def render(self, name: str, values: Mapping[str, object]) -> str:
        """Read a file and substitute its @PLACEHOLDER@ markers.

        Deliberately not str.format or f-strings: these documents are JSON,
        ini and GRUB theme files, all of which use braces for their own
        purposes. A marker with no value is an error rather than a silently
        empty string, because a half-rendered config file is harder to diagnose
        than a missing one.

        Values are a mapping rather than keyword arguments. A test caught the
        reason: with **values, a document containing @NAME@ collided with this
        method's own `name` parameter.
        """
        return self.substitute(self.read(name), values, source=name)

    @staticmethod
    def substitute(
        text: str, values: Mapping[str, object], source: str = "<text>"
    ) -> str:
        missing: list[str] = []

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key.lower() not in values:
                missing.append(key)
                return match.group(0)
            return str(values[key.lower()])

        rendered = _PLACEHOLDER.sub(replace, text)
        if missing:
            raise MissingPlaceholder(
                f"{source} needs {', '.join(sorted(set(missing)))}"
            )
        return rendered

    def exists(self, name: str) -> bool:
        return self._entry(name).is_file()
