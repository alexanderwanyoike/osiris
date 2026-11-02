"""Skills Osiris proposes (#154). A proposal is read in full on a card under
the answer and written among the person's own skills only when they keep it."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

#: Where the person's own skills are kept, under their home.
SKILLS = ".config/opencode/skills"


@dataclass(frozen=True)
class Proposal:
    #: Its id, lower-case words joined by hyphens, which names its folder.
    name: str
    description: str
    #: What it says, the skill itself.
    body: str


def skill_file(proposal: Proposal) -> str:
    """A SKILL.md the Engine reads: its name and description up front."""
    return (
        f"---\nname: {proposal.name}\ndescription: {proposal.description}\n---\n\n"
        f"{proposal.body.strip()}\n"
    )


def skill_path(home: Path, proposal: Proposal) -> Path:
    return home / SKILLS / proposal.name / "SKILL.md"


def plain(name: str) -> bool:
    """Lower-case letters and digits, joined by single hyphens: it names a
    folder, so nothing in it may lead elsewhere."""
    return re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) is not None
