"""Past Conversations grouped as the sidebar shows them (CONTEXT.md: a
Conversation belongs to at most one Project, the folder it was started in)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from osiris.harness.engine import Past


@dataclass
class Project:
    name: str
    folder: Path
    conversations: list[Past] = field(default_factory=list)


def group(pasts: list[Past], home: Path) -> tuple[list[Project], list[Past]]:
    """Projects with their Conversations, and the Conversations with none.

    Both keep the order given, newest first, so a Project's place is that of
    its most recent Conversation.
    """
    projects: dict[Path, Project] = {}
    loose: list[Past] = []
    for past in pasts:
        if past.directory == home:
            loose.append(past)
            continue
        project = projects.setdefault(
            past.directory, Project(past.directory.name, past.directory)
        )
        project.conversations.append(past)
    return list(projects.values()), loose
