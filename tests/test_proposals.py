"""Skills Osiris proposes (#154): read in full, written only when accepted."""

from __future__ import annotations

from pathlib import Path

from osiris.harness.proposals import Proposal, skill_file, skill_path

TIDY = Proposal("tidy-imports", "Sort and group Python imports", "Run ruff.")


def test_a_kept_proposal_is_a_skill_file_the_engine_reads() -> None:
    assert skill_file(TIDY) == (
        "---\n"
        "name: tidy-imports\n"
        "description: Sort and group Python imports\n"
        "---\n"
        "\n"
        "Run ruff.\n"
    )


def test_it_is_kept_among_the_persons_own_skills() -> None:
    home = Path("/home/tester")
    assert skill_path(home, TIDY) == (
        home / ".config/opencode/skills/tidy-imports/SKILL.md"
    )


def test_only_a_plain_name_can_name_a_skill() -> None:
    from osiris.harness.proposals import plain

    assert plain("tidy-imports")
    assert plain("review2")
    assert not plain("../etc")
    assert not plain("Tidy Imports")
    assert not plain("")
    assert not plain("-x")


def test_a_description_with_a_colon_or_a_quote_still_reads_as_one_value() -> None:
    """Front matter is YAML: unquoted, "Use when: x" would not parse."""
    import json

    awkward = Proposal("tidy-imports", 'Use when: imports are "messy"', "Run ruff.")
    line = next(
        line
        for line in skill_file(awkward).splitlines()
        if line.startswith("description:")
    )
    assert json.loads(line.removeprefix("description: ")) == awkward.description
