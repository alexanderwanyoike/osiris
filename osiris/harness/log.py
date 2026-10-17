"""The Harness log: everything sent to a model and everything done, kept.

One JSON object per line, appended and never rewritten, so the person can read
it with any tool and nothing in it changes after the fact.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from osiris.platform import FileSystem

#: Relative to the home: the person's data, not configuration.
LOG_FILE = ".local/share/osiris/harness/log.jsonl"


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
