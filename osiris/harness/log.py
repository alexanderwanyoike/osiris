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

    def programs_made(self) -> list[tuple[str, str]]:
        """Each Program the Harness made, and the session that made it."""
        made: list[tuple[str, str]] = []
        session = ""
        for entry in self._entries():
            session = entry.get("session", session)
            undo = entry.get("undo") or {}
            if entry["kind"] == "changed" and undo.get("action") == "trash_program":
                made.append((session, entry["program"]))
        return made

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
