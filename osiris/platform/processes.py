"""Who a running process is, as the kernel reports it in /proc.

``Processes`` is the port; ``ProcFs`` reads /proc.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

PROC = Path("/proc")


@dataclass(frozen=True)
class Process:
    pid: int
    parent: int
    #: The kernel's short name for it, from the file it executed.
    name: str
    uid: int
    euid: int
    cmdline: tuple[str, ...]
    #: None where the kernel will not say, as for a set-uid program run by
    #: someone else.
    exe: str | None


@runtime_checkable
class Processes(Protocol):
    def get(self, pid: int) -> Process | None:
        """The process, or None if there is none by that number."""
        ...


class ProcFs:
    def __init__(self, root: Path = PROC) -> None:
        self._root = root

    def get(self, pid: int) -> Process | None:
        folder = self._root / str(pid)
        try:
            status = dict(
                line.split(":", 1)
                for line in (folder / "status").read_text().splitlines()
                if ":" in line
            )
            raw = (folder / "cmdline").read_bytes()
        except OSError:
            return None
        uids = status["Uid"].split()
        return Process(
            pid=pid,
            parent=int(status["PPid"]),
            name=status["Name"].strip(),
            uid=int(uids[0]),
            euid=int(uids[1]),
            cmdline=_arguments(raw),
            exe=_exe(folder),
        )


def _arguments(raw: bytes) -> tuple[str, ...]:
    parts = raw.split(b"\0")
    if parts[-1] == b"":
        parts.pop()
    return tuple(part.decode(errors="replace") for part in parts)


def _exe(folder: Path) -> str | None:
    try:
        return str((folder / "exe").readlink())
    except OSError:
        return None
