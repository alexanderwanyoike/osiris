"""The reviewer Thoth asks before it calls a Program done (#161): one of the
Engine's own subagents, with its instructions shipped as an Engine skill."""

from __future__ import annotations

import re
from fnmatch import fnmatchcase

from osiris.resources.loader import Resources

AGENT = "engine/agents/reviewer.md"

_RULE = re.compile(
    r"- action: \"?([^\"\n]+)\"?\n\s+resource: \"?([^\"\n]+)\"?\n\s+effect: (\w+)"
)


def effect(action: str, resource: str) -> str:
    """What the reviewer's own rules decide, the last match winning as in the
    Engine; with no match the Engine's own default would apply."""
    found = "unmatched"
    for rule_action, rule_resource, rule_effect in _RULE.findall(
        Resources().read(AGENT)
    ):
        if fnmatchcase(action, rule_action) and fnmatchcase(resource, rule_resource):
            found = rule_effect
    return found


def test_the_reviewer_runs_only_as_a_subagent() -> None:
    """A subagent starts in a fresh child session: no part in the building."""
    assert "\nmode: subagent\n" in Resources().read(AGENT)


def test_the_reviewer_cannot_change_anything() -> None:
    assert effect("edit", "main.py") == "deny"
    assert effect("shell", "rm -rf src") == "deny"
    assert effect("subagent", "general") == "deny"


def test_the_reviewer_can_read_the_program_and_its_history() -> None:
    assert effect("read", "/home/tester/Code/timer/main.py") == "allow"
    assert effect("grep", "def tick") == "allow"
    assert effect("shell", "git diff abc123") == "allow"
    assert effect("shell", "git log --oneline") == "allow"
    assert effect("skill", "review") == "allow"
