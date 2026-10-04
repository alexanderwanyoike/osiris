"""Who is running, and where their home is.

A module for one question because getting it wrong is silent. Parts of this
codebase are invoked through `su <user> -c` - from the installer, from a
provisioning script - and `$HOME` is still root's when they are. Previews,
themes and configuration then land in /root where the user never sees them.
"""

from __future__ import annotations

import os
import pwd
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class Identity(Protocol):
    """The account a process is running as."""

    @property
    def uid(self) -> int: ...

    @property
    def gid(self) -> int: ...

    @property
    def name(self) -> str: ...

    @property
    def home(self) -> Path: ...

    def is_root(self) -> bool: ...


class SystemIdentity:
    """The real account, asked of the process rather than the environment."""

    def __init__(self, uid: int | None = None) -> None:
        self._uid = os.getuid() if uid is None else uid

    @property
    def _entry(self) -> pwd.struct_passwd | None:
        try:
            return pwd.getpwuid(self._uid)
        except KeyError:
            return None

    @property
    def uid(self) -> int:
        return self._uid

    @property
    def gid(self) -> int:
        entry = self._entry
        return entry.pw_gid if entry else os.getgid()

    @property
    def name(self) -> str:
        entry = self._entry
        return entry.pw_name if entry else str(self._uid)

    @property
    def home(self) -> Path:
        entry = self._entry
        # Deliberately not Path.home(), which trusts $HOME. See the module
        # docstring: under `su` that is root's home, not the user's.
        return Path(entry.pw_dir) if entry else Path.home()

    def is_root(self) -> bool:
        return self._uid == 0


@dataclass(frozen=True)
class FakeIdentity:
    """A stand-in, so tests never depend on who runs them."""

    uid: int = 1000
    gid: int = 1000
    name: str = "tester"
    home: Path = Path("/home/tester")

    def is_root(self) -> bool:
        return self.uid == 0


def desktop_users() -> list[pwd.struct_passwd]:
    """Real human accounts with a home directory on disk."""
    return [
        entry
        for entry in pwd.getpwall()
        if 1000 <= entry.pw_uid < 60000 and Path(entry.pw_dir).is_dir()
    ]
