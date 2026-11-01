"""The careful rules a fresh install starts with, written into the Engine's own
config so the same rules hold wherever the Engine is used (ADR 0020)."""

from __future__ import annotations

import json
from fnmatch import fnmatchcase
from pathlib import Path

from osiris.harness.rules import write_starting_rules
from osiris.platform import FakeFileSystem

HOME = Path("/home/tester")
ENGINE = HOME / ".config/opencode/opencode.json"


def effect(rules: list[dict[str, str]], action: str, resource: str) -> str:
    """What the Engine decides: the last rule whose action and resource match."""
    matching = [
        rule["effect"]
        for rule in rules
        if fnmatchcase(action, rule["action"]) and fnmatchcase(resource, rule["resource"])
    ]
    return matching[-1]


def test_with_no_rules_the_engine_starts_with_careful_ones() -> None:
    files = FakeFileSystem()
    write_starting_rules(files, HOME)
    rules = json.loads(files.read(ENGINE))["permissions"]
    assert effect(rules, "read", "/home/tester/notes.txt") == "allow"
    assert effect(rules, "read", "/home/tester/.env") == "ask"
    assert effect(rules, "shell", "ls") == "ask"
    assert effect(rules, "edit", "notes.txt") == "ask"
    assert effect(rules, "external_directory", "/etc/*") == "ask"
    assert effect(rules, "osiris_apply_theme", "*") == "allow"
    assert effect(rules, "someone_elses_tool", "*") == "ask"
