"""The careful rules a fresh install starts with, in the Engine's own config
(ADR 0020). The Engine reads them; the Harness only writes them where none are.
"""

from __future__ import annotations

import json
from pathlib import Path

from osiris.platform import FileSystem

ENGINE_CONFIG = ".config/opencode/opencode.json"
SCHEMA = "https://opencode.ai/config.json"


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
    _start(files, home / ENGINE_CONFIG, CAREFUL)
    _start(files, home / CODE_CONFIG, CODE)


def _start(files: FileSystem, path: Path, rules: list[dict[str, str]]) -> None:
    if files.exists(path.with_suffix(".jsonc")):
        return
    try:
        config = json.loads(files.read(path)) if files.exists(path) else {"$schema": SCHEMA}
    except json.JSONDecodeError:
        return
    if "permissions" in config:
        return
    config["permissions"] = rules
    files.write(path, json.dumps(config, indent=2) + "\n")
