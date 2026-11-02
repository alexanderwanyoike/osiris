"""The careful rules a fresh install starts with, in the Engine's own config
(ADR 0020). The Engine reads them; the Harness only writes them where none are.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from osiris.harness.engine_config import ENGINE_CONFIG, edit
from osiris.platform import FileSystem


def _rule(action: str, resource: str, effect: str) -> dict[str, str]:
    return {"action": action, "resource": resource, "effect": effect}


#: The Engine's base rules allow nearly everything; these ask first instead,
#: then allow what only looks or has an Undo. The last match wins, so the
#: `.env` asks follow the read allow they narrow.
CAREFUL = [
    _rule("*", "*", "ask"),
    *(
        _rule(action, "*", "allow")
        for action in (
            "read",
            "glob",
            "grep",
            "webfetch",
            "websearch",
            "question",
            "skill",
            "subagent",
            "execute",
            "todowrite",
            "osiris_*",
        )
    ),
    _rule("read", "*.env", "ask"),
    _rule("read", "*.env.*", "ask"),
    _rule("read", "*.env.example", "allow"),
    _rule("external_directory", "*", "ask"),
]


#: Read by every Project below ~/Code, where Programs are made.
CODE_CONFIG = "Code/.opencode/opencode.json"
#: Edits inside a Project: a Program's changes are commits, so each has an Undo.
CODE = [_rule("edit", "*", "allow")]


def write_starting_rules(files: FileSystem, home: Path) -> None:
    """Add the starting rules to each config that has none. A config with
    rules, even none, or that is not plain JSON is the person's and is left."""
    edit(
        files, home / ENGINE_CONFIG, lambda config: _add(config, "permissions", CAREFUL)
    )
    edit(files, home / CODE_CONFIG, lambda config: _add(config, "permissions", CODE))


def switch_on_task_list(files: FileSystem, home: Path) -> None:
    """Unless the person has switched it themselves."""
    edit(
        files,
        home / ENGINE_CONFIG,
        lambda config: _add(config.setdefault("experimental", {}), "todo", True),
    )


def _add(config: dict[str, Any], key: str, value: object) -> bool:
    if key in config:
        return False
    config[key] = value
    return True
