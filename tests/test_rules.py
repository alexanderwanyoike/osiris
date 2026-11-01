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
        if fnmatchcase(action, rule["action"])
        and fnmatchcase(resource, rule["resource"])
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


def test_what_else_the_engines_config_says_is_kept() -> None:
    files = FakeFileSystem()
    files.write(ENGINE, json.dumps({"model": "openai/gpt-5.5", "snapshots": True}))
    write_starting_rules(files, HOME)
    config = json.loads(files.read(ENGINE))
    assert config["model"] == "openai/gpt-5.5"
    assert config["snapshots"] is True
    assert config["permissions"]


def test_rules_the_person_has_are_never_overwritten() -> None:
    """Not even an empty list, which keeps the Engine's own defaults."""
    for theirs in ([], [{"action": "*", "resource": "*", "effect": "allow"}]):
        files = FakeFileSystem()
        files.write(ENGINE, json.dumps({"permissions": theirs}))
        write_starting_rules(files, HOME)
        assert json.loads(files.read(ENGINE))["permissions"] == theirs


def test_a_config_that_is_not_plain_json_is_left_alone() -> None:
    """The Engine also reads JSON with comments, which cannot be rewritten
    without losing them."""
    files = FakeFileSystem()
    commented = '{\n  // my model\n  "model": "openai/gpt-5.5"\n}\n'
    files.write(ENGINE, commented)
    write_starting_rules(files, HOME)
    assert files.read(ENGINE) == commented


def test_a_person_who_keeps_their_config_as_jsonc_is_left_alone() -> None:
    """A second file beside it would add rules they never see."""
    files = FakeFileSystem()
    files.write(ENGINE.with_suffix(".jsonc"), '{"model": "openai/gpt-5.5"}')
    write_starting_rules(files, HOME)
    assert not files.exists(ENGINE)


CODE = HOME / "Code/.opencode/opencode.json"


def test_edits_inside_a_project_in_code_are_allowed() -> None:
    """Inside a Project the Engine names an edit by its path from the Project,
    so the rule lives in a config every Project in ~/Code reads."""
    files = FakeFileSystem()
    write_starting_rules(files, HOME)
    rules = json.loads(files.read(CODE))["permissions"]
    assert effect(rules, "edit", "main.py") == "allow"
