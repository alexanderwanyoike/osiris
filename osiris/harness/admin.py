"""Admin password requests: sudo asking the person, through Osiris, for the
password, and the guards on who may ask (ADR 0018).

The agent's sudo runs with ``-A``, so sudo runs the askpass helper, which asks
the Harness over D-Bus; the Harness shows an admin password card in the
Conversation whose command it is. Everything here decides; the helper and the
Harness only draw and carry the answer.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from osiris.platform.processes import Process, Processes

#: sudo's options that take a value (sudo 1.9.17, ``sudo -h``), short and long.
#: ``-h`` takes one only when it is attached, as ``-hhost``.
_SHORT_WITH_VALUE = frozenset("aCcDgpRrTtUu")
_LONG_WITH_VALUE = {
    "auth-type": "a",
    "close-from": "C",
    "login-class": "c",
    "chdir": "D",
    "group": "g",
    "prompt": "p",
    "chroot": "R",
    "role": "r",
    "command-timeout": "T",
    "type": "t",
    "other-user": "U",
    "user": "u",
}


@dataclass(frozen=True)
class Request:
    """What an asking sudo will run, and as whom."""

    command: tuple[str, ...]
    user: str = "root"


def _is_sudo(process: Process) -> bool:
    """The person cannot read a set-uid program's executable, so sudo is known
    by its name and by running as root; only a set-uid program can make a
    process of theirs root, and of those only sudo runs a helper before it has
    a password."""
    return process.name == "sudo" and process.euid == 0


def asking_sudo(processes: Processes, helper: int) -> Process | None:
    """The sudo that started the helper ``helper``, if it is a genuine one
    running as root for the same person; None means refuse."""
    found = processes.get(helper)
    if found is None or found.euid == 0:
        return None
    parent = processes.get(found.parent)
    if parent is None or not _is_sudo(parent) or parent.uid != found.uid:
        return None
    return parent


class _Options:
    """sudo's options, read as sudo reads them: up to the first argument that
    is not one, or ``--``."""

    def __init__(self, arguments: Sequence[str]) -> None:
        self._arguments = arguments
        self.values: dict[str, str] = {}
        self.at = 0

    def read(self) -> None:
        while self.at < len(self._arguments):
            argument = self._arguments[self.at]
            self.at += 1
            if argument == "--":
                return
            if argument.startswith("--"):
                self._long(argument[2:])
            elif argument.startswith("-") and argument != "-":
                self._short(argument[1:])
            else:
                self.at -= 1
                return

    def _next(self) -> str:
        value = self._arguments[self.at] if self.at < len(self._arguments) else ""
        self.at += 1
        return value

    def _long(self, option: str) -> None:
        name, given, value = option.partition("=")
        if name in _LONG_WITH_VALUE:
            self.values[_LONG_WITH_VALUE[name]] = value if given else self._next()

    def _short(self, bundle: str) -> None:
        for index, flag in enumerate(bundle):
            attached = bundle[index + 1 :]
            if flag in _SHORT_WITH_VALUE or (flag == "h" and attached):
                self.values[flag] = attached or self._next()
                return
            self.values.setdefault(flag, "")


def request_of(cmdline: Sequence[str]) -> Request:
    """What the sudo with this command line will run."""
    arguments = list(cmdline[1:])
    options = _Options(arguments)
    options.read()
    return Request(
        command=tuple(arguments[options.at :]),
        user=options.values.get("u") or "root",
    )
