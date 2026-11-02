"""The Engine's own config file, shared by what Osiris writes into it."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from osiris.platform import FileSystem

ENGINE_CONFIG = ".config/opencode/opencode.json"
SCHEMA = "https://opencode.ai/config.json"


def read(files: FileSystem, path: Path) -> dict[str, Any]:
    """The config, or nothing where there is none or it is not plain JSON."""
    try:
        loaded: dict[str, Any] = json.loads(files.read(path))
    except OSError, json.JSONDecodeError:
        return {}
    return loaded


def edit(
    files: FileSystem, path: Path, change: Callable[[dict[str, Any]], bool]
) -> bool:
    """Change a config the Engine reads, if it is plain JSON and ``change`` says
    it changed anything; a commented one, or one kept as .jsonc, is left.
    Whether the config could be changed."""
    if files.exists(path.with_suffix(".jsonc")):
        return False
    try:
        config = json.loads(files.read(path)) if files.exists(path) else {}
    except json.JSONDecodeError:
        return False
    if change(config):
        files.write(path, json.dumps({"$schema": SCHEMA, **config}, indent=2) + "\n")
    return True
