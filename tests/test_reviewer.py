"""The reviewer Thoth asks before it calls a Program done (#161): one of the
Engine's own subagents, with its instructions shipped as an Engine skill."""

from __future__ import annotations

import re
from fnmatch import fnmatchcase
from pathlib import Path

from osiris.platform import FakeFileSystem
from osiris.resources.loader import Resources

AGENT = "engine/agents/reviewer.md"
HOME = Path("/home/tester")
ENGINE = HOME / ".config/opencode"

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


SKILL = "engine/skills/review/SKILL.md"


def test_the_review_skill_is_shown_to_the_model() -> None:
    """The Engine advertises only a skill with a description."""
    head = Resources().read(SKILL).split("---")[1]
    assert "\nname: review\n" in head
    assert "\ndescription: " in head


def test_the_review_reports_three_axes_side_by_side_under_one_verdict() -> None:
    skill = Resources().read(SKILL)
    for axis in ("## Spec", "## Standards", "## Bugs"):
        assert axis in skill
    assert "Verdict: pass" in skill
    assert "partial" in skill and "fail" in skill
    assert "CODING_STANDARDS.md" in skill


def test_the_skills_it_is_adapted_from_are_credited_under_their_licences() -> None:
    resources = Resources()
    assert "Copyright (c) 2026 Matt Pocock" in resources.read(
        "engine/skills/review/LICENSE-MIT"
    )
    assert "Apache License" in resources.read("engine/skills/review/LICENSE-APACHE")
    notice = resources.read("engine/skills/review/NOTICE.md")
    assert "https://github.com/mattpocock/skills" in notice
    assert "https://github.com/anthropics/claude-plugins-official" in notice


def test_the_reviewer_and_its_skill_are_given_to_the_engine() -> None:
    from osiris.harness.reviewer import write_reviewer

    files = FakeFileSystem()
    write_reviewer(files, HOME)
    resources = Resources()
    for name in (
        "agents/reviewer.md",
        "skills/review/SKILL.md",
        "skills/review/NOTICE.md",
        "skills/review/LICENSE-MIT",
        "skills/review/LICENSE-APACHE",
    ):
        assert files.read(ENGINE / name) == resources.read(f"engine/{name}")


def test_a_reviewer_the_person_changed_is_kept() -> None:
    """What Osiris gives is the person's to change, and no upgrade undoes it."""
    from osiris.harness.reviewer import write_reviewer

    files = FakeFileSystem()
    files.write(ENGINE / "skills/review/SKILL.md", "my own review")
    write_reviewer(files, HOME)
    assert files.read(ENGINE / "skills/review/SKILL.md") == "my own review"
