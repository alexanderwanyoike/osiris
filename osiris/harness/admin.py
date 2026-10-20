"""Admin password requests: sudo asking the person, through Osiris, for the
password, and the guards on who may ask (ADR 0018).

The agent's sudo runs with ``-A``, so sudo runs the askpass helper, which asks
the Harness over D-Bus; the Harness shows an admin password card in the
Conversation whose command it is. Everything here decides; the helper and the
Harness only draw and carry the answer.
"""

from __future__ import annotations

import re
import shlex
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from itertools import takewhile
from pathlib import PurePosixPath

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
_LONG_FLAGS = {"shell": "s", "login": "i", "edit": "e"}


#: Programs whose ``-c`` runs a string of shell.
SHELLS = frozenset({"sh", "bash", "zsh", "dash", "ksh", "fish"})
_INTERPRETER = re.compile(r"(?:sh|bash|zsh|dash|ksh|fish|python[\d.]*|perl|ruby|node)")
#: Where the system's own programs are, root's to change. A program named with
#: no folder is found in these too: Arch's sudoers sets secure_path to them.
SYSTEM_FOLDERS = (
    "/usr/bin/",
    "/usr/sbin/",
    "/bin/",
    "/sbin/",
    "/usr/local/bin/",
    "/usr/local/sbin/",
)
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")


class Kind(Enum):
    COMMAND = "command"
    #: A string of shell, which can do anything, so it is shown in full.
    SHELL = "shell"
    #: A program of the person's own or an interpreter given a file: what it
    #: does is in a file the card does not show.
    SCRIPT = "script"


def _kind(command: Sequence[str]) -> Kind:
    words = list(command)
    while words and _ASSIGNMENT.fullmatch(words[0]):
        words.pop(0)
    if not words:
        return Kind.COMMAND
    name = PurePosixPath(words[0]).name
    options = list(takewhile(lambda word: word.startswith("-"), words[1:]))
    runs_a_string = any(
        not option.startswith("--") and "c" in option for option in options
    )
    if name in SHELLS and runs_a_string:
        return Kind.SHELL
    if "/" in words[0] and not words[0].startswith(SYSTEM_FOLDERS):
        return Kind.SCRIPT
    given_a_file = len(words) > 1 + len(options)
    if _INTERPRETER.fullmatch(name) and given_a_file and not runs_a_string:
        return Kind.SCRIPT
    return Kind.COMMAND


@dataclass(frozen=True)
class Request:
    """What an asking sudo will run, and as whom."""

    command: tuple[str, ...]
    user: str = "root"
    #: Run through the target user's shell, as ``sudo -s`` and ``-i`` do.
    shell: bool = False

    @property
    def kind(self) -> Kind:
        return Kind.SHELL if self.shell else _kind(self.command)

    @property
    def shown(self) -> str:
        if self.command:
            return shlex.join(self.command)
        if self.shell:
            return "an interactive shell"
        return "nothing: sudo only checks the password"

    @property
    def note(self) -> str | None:
        """What the person should know beyond the command itself."""
        if self.kind is Kind.SHELL:
            return f"A shell command, shown in full: all of it runs as {self.user}."
        if self.kind is Kind.SCRIPT:
            return "Runs a script; its contents are not shown."
        return None


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
        elif name in _LONG_FLAGS:
            self.values.setdefault(_LONG_FLAGS[name], "")

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
    command = tuple(arguments[options.at :])
    if "e" in options.values or PurePosixPath(cmdline[0]).name == "sudoedit":
        command = ("sudoedit", *command)
    return Request(
        command=command,
        user=options.values.get("u") or "root",
        shell=bool({"s", "i"} & options.values.keys()),
    )
