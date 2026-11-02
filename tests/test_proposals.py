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
