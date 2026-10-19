"""Whether Osiris was upgraded under a process that lives for the session.

osiris-setup replaces the code under /usr/share/osiris and rewrites MARKER as
its last step. A resident process reads MARKER when it starts and restarts once
it changes, rather than mixing old modules in memory with new ones on disk.
"""

from __future__ import annotations

from pathlib import Path

from osiris.platform import FileSystem

MARKER = Path("/usr/share/osiris/setup-ran")


class Upgrade:
    def __init__(self, files: FileSystem, marker: Path = MARKER) -> None:
        self._files = files
        self._marker = marker
        self._started = self._read()

    def _read(self) -> str | None:
        if not self._files.exists(self._marker):
            return None
        return self._files.read(self._marker)

    def happened(self) -> bool:
        """Whether setup has run again since this process started."""
        return self._read() != self._started
