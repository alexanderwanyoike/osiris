"""Past Conversations grouped as the sidebar shows them (CONTEXT.md: a
Conversation belongs to at most one Project, the folder it was started in)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from osiris.harness.engine import Past

#: Where Programs, and so their Projects, live in a home (ADR 0017).
CODE_DIR = "Code"


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


def misplaced(
    pasts: list[Past],
    worked_on: list[tuple[str, str]],
    home: Path,
    exists: Callable[[Path], bool],
) -> list[tuple[str, Path]]:
    """Conversations still in no Project although they worked on a Program
    whose folder is there, and the Project each belongs in: those from before
    the Harness moved them itself."""
    homeless = {past.session for past in pasts if past.directory == home}
    found = []
    for session, program in worked_on:
        folder = home / CODE_DIR / program
        if session in homeless and exists(folder):
            found.append((session, folder))
            homeless.discard(session)
    return found


def project_program(directory: Path, home: Path) -> str | None:
    """The Program whose source is the Project a Conversation runs in, if any."""
    if directory.parent == home / CODE_DIR:
        return directory.name
    return None
