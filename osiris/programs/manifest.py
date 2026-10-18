"""The Program manifest, and the menu entry made from it (docs/PROGRAMS.md).

The manifest is the one file in a Program's source that is Osiris's own; the
menu entry is derived from it on install. A model writes manifests, so a bad
one is refused with a reason it can act on.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import PurePath, PurePosixPath
from typing import Any

from osiris.model.names import slug

MANIFEST_FILE = "osiris-program.json"

#: Shown when a Program brings no icon of its own.
GENERIC_ICON = "application-x-executable"

#: Characters that make the Desktop Entry spec require an argument be quoted.
_RESERVED = set(" \t\n\"'\\><~|&;$*?#()`")


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class Manifest:
    name: str
    label: str
    description: str
    icon: str | None
    build: tuple[str, ...] | None
    run: tuple[str, ...]
    terminal: bool = False


def _text(fields: dict[str, Any], key: str) -> str:
    value = fields.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"The manifest needs {key}, as text")
    if "\n" in value or "\r" in value:
        raise ManifestError(f"{key} must be one line")
    return value


def _words(fields: dict[str, Any], key: str) -> tuple[str, ...]:
    value = fields[key]
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(w, str) and w for w in value)
    ):
        raise ManifestError(
            f'{key} must be a list of words, not a shell line: ["python3", "main.py"]'
        )
    return tuple(value)


def _inside(path: str) -> str:
    parts = PurePosixPath(path)
    if parts.is_absolute() or ".." in parts.parts:
        raise ManifestError(f"{path} must be a file inside the Program")
    return path


def parse(text: str) -> Manifest:
    try:
        fields = json.loads(text)
    except json.JSONDecodeError as error:
        raise ManifestError(f"The manifest is not valid JSON: {error}") from error
    if not isinstance(fields, dict):
        raise ManifestError("The manifest must be a JSON object")
    name = _text(fields, "name")
    if slug(name) != name:
        raise ManifestError(
            f"name must be lower case words joined by hyphens, like {slug(name)}"
        )
    if "run" not in fields:
        raise ManifestError("The manifest needs run, the words that start it")
    icon = fields.get("icon")
    if icon is not None and not isinstance(icon, str):
        raise ManifestError("icon must be the name of a file inside the Program")
    terminal = fields.get("terminal", False)
    if not isinstance(terminal, bool):
        raise ManifestError("terminal must be true or false")
    return Manifest(
        name=name,
        label=_text(fields, "label"),
        description=_text(fields, "description"),
        icon=_inside(icon) if icon else None,
        build=_words(fields, "build") if fields.get("build") is not None else None,
        run=_words(fields, "run"),
        terminal=terminal,
    )


def dump(manifest: Manifest) -> str:
    fields = asdict(manifest)
    for key in ("build", "run"):
        if fields[key] is not None:
            fields[key] = list(fields[key])
    return json.dumps(fields, indent=4) + "\n"


def _quoted(word: str) -> str:
    """One argument as the Desktop Entry spec's Exec key wants it."""
    word = word.replace("%", "%%")
    if not _RESERVED.intersection(word):
        return word
    escaped = "".join(f"\\{c}" if c in '"`$\\' else c for c in word)
    # The string-level escape applies on top of the quoting one.
    return '"' + escaped.replace("\\", "\\\\") + '"'


def desktop_entry(manifest: Manifest, installed: PurePath) -> str:
    """The menu entry for the copy of ``manifest``'s Program at ``installed``."""
    first, *rest = manifest.run
    program = f"{installed}/{first}" if "/" in first else first
    icon = f"{installed}/{manifest.icon}" if manifest.icon else GENERIC_ICON
    fields = {
        "Type": "Application",
        "Name": manifest.label,
        "Comment": manifest.description,
        "Exec": " ".join(_quoted(word) for word in (program, *rest)),
        "Path": str(installed),
        "Icon": icon,
        "Terminal": "true" if manifest.terminal else "false",
        "Categories": "Utility;",
        "X-Osiris-Program": manifest.name,
    }
    return "[Desktop Entry]\n" + "".join(f"{k}={v}\n" for k, v in fields.items())
