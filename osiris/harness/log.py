"""The Harness log: everything sent to a model and everything done, kept.

One JSON object per line, appended and never rewritten, so the person can read
it with any tool and nothing in it changes after the fact; the one exception is
deleting a Conversation, which erases it from here too (CONTEXT.md).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from osiris.platform import FileSystem

#: Relative to the home: the person's data, not configuration.
LOG_FILE = ".local/share/osiris/harness/log.jsonl"


@dataclass(frozen=True)
class Change:
    """Something an action changed, and the step that reverses it, if any."""

    summary: str
    undo: Mapping[str, str] | None
    program: str | None = None


def _now() -> datetime:
    return datetime.now(UTC)


class HarnessLog:
    def __init__(
        self,
        files: FileSystem,
        path: Path,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self._files = files
        self._path = path
        self._clock = clock

    def write(self, kind: str, **fields: object) -> None:
        entry = {"time": self._clock().isoformat(), "kind": kind, **fields}
        self._files.append(self._path, json.dumps(entry, ensure_ascii=False) + "\n")

    def programs_worked_on(self) -> list[tuple[str, str]]:
        """Each session that changed a Program, and the first Program it changed."""
        first: dict[str, str] = {}
        session = ""
        for entry in self._entries():
            session = entry.get("session", session)
            if entry["kind"] == "changed" and entry.get("program"):
                first.setdefault(session, entry["program"])
        return list(first.items())

    def programs_of(self, session: str) -> list[str]:
        """The Programs a session changed, each once, in the order it first did."""
        changed: dict[str, None] = {}
        current = ""
        for entry in self._entries():
            current = entry.get("session", current)
            if (
                current == session
                and entry["kind"] == "changed"
                and entry.get("program")
            ):
                changed.setdefault(entry["program"])
        return list(changed)

    def forget(self, session: str) -> None:
        """Erase everything logged for a deleted Conversation."""
        kept = []
        current = ""
        for entry in self._entries():
            current = entry.get("session", current)
            if current != session:
                kept.append(json.dumps(entry, ensure_ascii=False) + "\n")
        if self._files.exists(self._path):
            self._files.write(self._path, "".join(kept))

    def tokens_spent(self, session: str) -> int:
        """The tokens a session's answers used, counted as the drawer counts
        them while it answers: input, output and reasoning."""
        return sum(
            entry["tokens"]["input"]
            + entry["tokens"]["output"]
            + entry["tokens"]["reasoning"]
            for entry in self._entries()
            if entry["kind"] == "answered" and entry.get("session") == session
        )

    def _entries(self) -> list[dict[str, Any]]:
        if not self._files.exists(self._path):
            return []
        return [json.loads(line) for line in self._files.read(self._path).splitlines()]

    def changes_by_question(self, session: str) -> list[list[Change]]:
        """For each question the session was asked, in order, the changes
        logged after it until the next question to any session."""
        questions: list[list[Change]] = []
        collecting = False
        for entry in self._entries():
            if entry["kind"] == "sent":
                collecting = entry.get("session") == session
                if collecting:
                    questions.append([])
            elif entry["kind"] == "changed" and collecting:
                questions[-1].append(
                    Change(entry["summary"], entry["undo"], entry.get("program"))
                )
        return questions

    def last_changes(self) -> list[Change]:
        """The changes logged since the last question was sent."""
        changes: list[Change] = []
        for entry in self._entries():
            if entry["kind"] == "sent":
                changes = []
            elif entry["kind"] == "changed":
                changes.append(
                    Change(entry["summary"], entry["undo"], entry.get("program"))
                )
        return changes
