"""The Harness log: everything sent to a model and everything done, kept.

One JSON object per line, appended and never rewritten, so the person can read
it with any tool and nothing in it changes after the fact.
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

    def _entries(self) -> list[dict[str, Any]]:
        if not self._files.exists(self._path):
            return []
        return [json.loads(line) for line in self._files.read(self._path).splitlines()]

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
