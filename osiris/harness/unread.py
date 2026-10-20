"""The Conversations with an answer the person has not seen yet.

Kept in a file in their home, so a restart of the Harness keeps them.
"""

from __future__ import annotations

from pathlib import Path

from osiris.harness.engine import Event, Failed, Finished
from osiris.platform import FileSystem

#: Relative to the home: state the Harness keeps, not the person's data.
UNREAD_FILE = ".local/state/osiris/harness/unread"


class Unread:
    def __init__(self, files: FileSystem, home: Path) -> None:
        self._files = files
        self._path = home / UNREAD_FILE

    def sessions(self) -> frozenset[str]:
        if not self._files.exists(self._path):
            return frozenset()
        return frozenset(self._files.read(self._path).split())

    def ended(self, event: Event, *, looking: bool) -> bool:
        """An answer is over; unread unless the person was looking at it.
        True when it became unread."""
        if looking or not isinstance(event, Finished | Failed):
            return False
        self._keep(self.sessions() | {event.session})
        return True

    def read(self, session: str) -> None:
        """Opened, or gone from the history: deleted or archived."""
        self._keep(self.sessions() - {session})

    def _keep(self, sessions: frozenset[str]) -> None:
        self._files.write(self._path, "".join(f"{s}\n" for s in sorted(sessions)))
