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
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from itertools import takewhile
from pathlib import PurePosixPath

from osiris.platform.processes import Process, Processes

#: The askpass helper, root's file, which the Harness answers.
HELPER = "/usr/lib/osiris/askpass"
#: How the helper runs: its interpreter in isolated mode, so nothing in the
#: person's environment or site folder is loaded into it.
HELPER_ARGV = ("/usr/bin/python3", "-I", HELPER)
#: Where the agent's sudo is, put first on the Engine's PATH.
AGENT_BIN = "/usr/lib/osiris/agent-bin"
AGENT_SUDO = f"{AGENT_BIN}/sudo"

#: The agent's sudo: the system's, with -A so it asks through the helper even
#: with no terminal, and -k so no earlier approval is reused and nothing is
#: kept for the next command (sudo's manual, -k).
AGENT_SUDO_SCRIPT = f"""#!{" ".join(HELPER_ARGV[:2])}
import os
import sys

os.execve(
    "/usr/bin/sudo",
    ["/usr/bin/sudo", "-k", "-A", *sys.argv[1:]],
    {{**os.environ, "SUDO_ASKPASS": "{HELPER}"}},
)
"""

#: The helper as installed; what it does is apps/harness/askpass.py.
HELPER_SCRIPT = f"""#!{" ".join(HELPER_ARGV[:2])}
import runpy

runpy.run_path("/usr/share/osiris/harness/askpass.py", run_name="__main__")
"""
_SYSTEM_PYTHON = re.compile(r"/usr/bin/python3(?:\.\d+)?")

#: Where the helper asks: an object on the Harness's own bus name.
BUS_NAME = "dev.osiris.Harness"
OBJECT_PATH = "/dev/osiris/Harness/Admin"
INTERFACE = "dev.osiris.Harness.Admin"
INTERFACE_XML = f"""<node>
  <interface name="{INTERFACE}">
    <method name="Ask">
      <arg name="command" type="as" direction="in"/>
      <arg name="prompt" type="s" direction="in"/>
      <arg name="approved" type="b" direction="out"/>
      <arg name="password" type="s" direction="out"/>
    </method>
  </interface>
</node>
"""
#: The Harness's refusal: the caller failed its checks, so nothing is shown.
REFUSED = f"{INTERFACE}.Refused"
#: Not a command of the agent's: the helper asks in a dialog of its own.
NOT_THE_AGENTS = f"{INTERFACE}.NotTheAgents"
#: D-Bus errors after which the helper asks in a dialog of its own: the
#: Harness is not running, is too old to have the interface, or says the
#: command is not its agent's.
_ASK_ITSELF_AFTER = frozenset(
    {
        NOT_THE_AGENTS,
        "org.freedesktop.DBus.Error.ServiceUnknown",
        "org.freedesktop.DBus.Error.NameHasNoOwner",
        "org.freedesktop.DBus.Error.UnknownObject",
        "org.freedesktop.DBus.Error.UnknownMethod",
    }
)


def asks_itself(error: str | None) -> bool:
    """Whether the helper, having asked the Harness and got the D-Bus error
    ``error``, asks the person itself."""
    return error in _ASK_ITSELF_AFTER


#: How long the helper waits for the person, in seconds.
ASK_TIMEOUT = 300
HARNESS_GIVES_UP = ASK_TIMEOUT - 10

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


def agent_environment(env: Mapping[str, str]) -> dict[str, str]:
    """``env`` as the Engine is to inherit it: the agent's sudo found first,
    and any other ``sudo -A`` in its commands asking through the helper."""
    folders = [f for f in env.get("PATH", "").split(":") if f and f != AGENT_BIN]
    return {**env, "PATH": ":".join([AGENT_BIN, *folders]), "SUDO_ASKPASS": HELPER}


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


def caller_sudo(processes: Processes, caller: int, *, uid: int) -> Process | None:
    """The genuine sudo behind ``caller``, if the caller is the helper it
    started for the account ``uid``; None means refuse.

    A process can rewrite its own command line, so the check that holds is the
    parent: only sudo, as root, starts the helper; the rest turns away other
    programs sudo was pointed at.
    """
    found = processes.get(caller)
    if (
        found is None
        or found.uid != uid
        or found.cmdline[: len(HELPER_ARGV)] != HELPER_ARGV
        or not _SYSTEM_PYTHON.fullmatch(found.exe or "")
    ):
        return None
    return asking_sudo(processes, caller)


#: Further up than any real chain of parents, so a cycle cannot hang the search.
_DEEPEST = 64


def descends_from(processes: Processes, pid: int, ancestor: int | None) -> bool:
    """Whether ``ancestor`` is among ``pid``'s parents."""
    if ancestor is None:
        return False
    found = processes.get(pid)
    for _ in range(_DEEPEST):
        if found is None or found.parent <= 1:
            return False
        if found.parent == ancestor:
            return True
        found = processes.get(found.parent)
    return False


def asking_program(processes: Processes, sudo: Process) -> str:
    """What to call the program that ran ``sudo``: the nearest of its parents
    that is not a shell."""
    found = processes.get(sudo.parent)
    for _ in range(_DEEPEST):
        if found is None:
            break
        named = PurePosixPath(found.cmdline[0]).name if found.cmdline else found.name
        if named.lstrip("-") not in SHELLS:
            return named
        found = processes.get(found.parent)
    return "an unknown program"


@dataclass(frozen=True)
class HarnessAnswer:
    """What came back when the helper asked the Harness: the password if the
    person allowed it, or the D-Bus error if the call failed."""

    password: str | None = None
    error: str | None = None


def helper_answer(
    processes: Processes,
    helper: int,
    *,
    ask_harness: Callable[[Request], HarnessAnswer],
    ask_person: Callable[[str, Request], str | None],
) -> str | None:
    """The password the helper ``helper`` hands to sudo, or None for none."""
    sudo = asking_sudo(processes, helper)
    if sudo is None:
        return None
    request = request_of(sudo.cmdline)
    answer = ask_harness(request)
    if answer.error is None:
        return answer.password
    if asks_itself(answer.error):
        return ask_person(asking_program(processes, sudo), request)
    return None


@dataclass(frozen=True)
class Refuse:
    """No card and no dialog: the caller is not who it must be."""

    reason: str


@dataclass(frozen=True)
class NotTheAgents:
    """A genuine request, but not from a Conversation: the helper asks itself."""

    request: Request


@dataclass(frozen=True)
class Show:
    """An admin password card, in the Conversation ``session``."""

    request: Request
    session: str


Verdict = Refuse | NotTheAgents | Show


def judge(
    processes: Processes,
    caller: int,
    sent: Sequence[str],
    *,
    uid: int,
    engine: int | None,
    session: str | None,
) -> Verdict:
    """What the Harness does with a request from the D-Bus caller ``caller``
    naming the command ``sent``, given the Engine's process and the session
    whose command runs sudo."""
    sudo = caller_sudo(processes, caller, uid=uid)
    if sudo is None:
        return Refuse("the caller is not the askpass helper of a root sudo")
    request = request_of(sudo.cmdline)
    if tuple(sent) != request.command:
        return Refuse("the command named is not the one sudo runs")
    if session is None or not descends_from(processes, sudo.pid, engine):
        return NotTheAgents(request)
    return Show(request, session)


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
