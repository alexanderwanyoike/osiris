"""The Conversations with an answer the person has not seen yet."""

from __future__ import annotations

from pathlib import Path

from osiris.harness.engine import Event, Failed, Finished
from osiris.platform import FileSystem


class Unread:
    def __init__(self, files: FileSystem, home: Path) -> None:
        self._files = files
        self._home = home
        self._sessions: set[str] = set()

    def sessions(self) -> frozenset[str]:
        return frozenset(self._sessions)

    def ended(self, event: Event, *, looking: bool) -> bool:
        """An answer is over; unread unless the person was looking at it.
        True when it became unread."""
        if looking or not isinstance(event, Finished | Failed):
            return False
        self._sessions.add(event.session)
        return True
