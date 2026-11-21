"""What a question changed, from the commits it made to Programs. Each commit
is recorded with the question in the Harness log, so this works for any
Program from any Conversation, reopened or not."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from osiris.harness.engine import FileChange
from osiris.harness.log import HarnessLog

_FILE = re.compile(r"^diff --git a/(.+) b/(.+)$", re.MULTILINE)


class ProgramHistory(Protocol):
    def commits_since(self, name: str, since: datetime) -> list[tuple[str, str]]: ...

    def held(self, name: str, commits: list[str]) -> list[str]: ...

    def label(self, name: str) -> str: ...


def credit_shell_commits(
    log: HarnessLog,
    history: ProgramHistory,
    session: str,
    project: str | None = None,
) -> None:
    """Log as the latest question's changes the commits made since it was
    asked, to the Programs it worked on or the ``project`` it runs in, that
    the Osiris tools did not log: those made with git in a shell (#219)."""
    asked = log.asked_at(session)
    questions = log.changes_by_question(session)
    if asked is None or not questions:
        return
    names = [change.program for change in questions[-1] if change.program]
    credited = {(change.undo or {}).get("commit") for change in questions[-1]}
    for name in dict.fromkeys(names + ([project] if project else [])):
        for commit, subject in history.commits_since(name, asked):
            if commit in credited:
                continue
            log.write(
                "changed",
                session=session,
                summary=f"{history.label(name)}: {subject}",
                undo={"action": "revert_commit", "name": name, "commit": commit},
                program=name,
            )


def standing_steps(
    history: ProgramHistory, steps: list[Mapping[str, str]]
) -> list[Mapping[str, str]] | None:
    """An answer's Undo steps, newest first, as git has them now; None if a
    later answer replaced what it made. A commit a branch still holds after a
    replaced one was made on top of that rewrite, so the answer did it itself."""
    made: dict[str, list[str]] = {}
    for step in steps:
        if step["action"] == "revert_commit":
            made.setdefault(step["name"], []).append(step["commit"])
    held = {c for name, commits in made.items() for c in history.held(name, commits)}
    kept: list[Mapping[str, str]] = []
    settled: set[str] = set()
    for step in steps:
        if step["action"] != "revert_commit":
            kept.append(step)
        elif step["commit"] in held:
            settled.add(step["name"])
            kept.append(step)
        elif step["name"] not in settled:
            return None
    return kept


def file_changes(program: str, patch: str) -> tuple[FileChange, ...]:
    """Each file in a commit's patch, named under its Program."""
    starts = [found.start() for found in _FILE.finditer(patch)]
    ends = [*starts[1:], len(patch)] if starts else []
    sections = [
        patch[start:end].rstrip("\n") for start, end in zip(starts, ends, strict=True)
    ]
    return tuple(_change(program, section) for section in sections)


def _change(program: str, section: str) -> FileChange:
    lines = section.split("\n")
    path = _FILE.match(lines[0])
    assert path is not None
    if any(line.startswith("new file mode") for line in lines[:4]):
        status = "added"
    elif any(line.startswith("deleted file mode") for line in lines[:4]):
        status = "deleted"
    else:
        status = "modified"
    hunks = next((i for i, line in enumerate(lines) if line.startswith("@@")), None)
    body = lines[hunks:] if hunks is not None else []
    return FileChange(
        f"{program}/{path.group(2)}",
        status,
        sum(1 for line in body if line.startswith("+")),
        sum(1 for line in body if line.startswith("-")),
        section,
    )
