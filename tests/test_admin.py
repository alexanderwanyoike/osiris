"""The admin password guards: who may ask for a password, for what, and where
the request is shown (ADR 0018)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from osiris.harness.admin import asking_sudo, request_of
from osiris.platform.processes import FakeProcesses, Process

ME = 1000
PROMPT = "[sudo] password for tester: "

ENGINE = Process(
    pid=50,
    parent=1,
    name="opencode",
    uid=ME,
    euid=ME,
    cmdline=("/usr/bin/opencode", "serve", "--service"),
    exe="/usr/bin/opencode",
)
SHELL = Process(
    pid=100,
    parent=50,
    name="bash",
    uid=ME,
    euid=ME,
    cmdline=("/usr/bin/bash", "-c", "sudo pacman -S cowsay"),
    exe="/usr/bin/bash",
)
# sudo is set-uid root: its effective user is root and the person cannot read
# its executable.
SUDO = Process(
    pid=200,
    parent=100,
    name="sudo",
    uid=ME,
    euid=0,
    cmdline=("/usr/bin/sudo", "-k", "-A", "pacman", "-S", "cowsay"),
    exe=None,
)
HELPER = Process(
    pid=300,
    parent=200,
    name="askpass",
    uid=ME,
    euid=ME,
    cmdline=("/usr/bin/python3", "-I", "/usr/lib/osiris/askpass", PROMPT),
    exe="/usr/bin/python3.14",
)


def table(*processes: Process) -> FakeProcesses:
    return FakeProcesses({p.pid: p for p in processes})


def genuine() -> FakeProcesses:
    return table(ENGINE, SHELL, SUDO, HELPER)


class TestTheHelpersParent:
    def test_is_the_genuine_sudo_that_started_it(self) -> None:
        assert asking_sudo(genuine(), HELPER.pid) == SUDO

    def test_attack_the_helper_run_directly_by_the_persons_shell(self) -> None:
        direct = replace(HELPER, parent=SHELL.pid)
        assert asking_sudo(table(ENGINE, SHELL, direct), HELPER.pid) is None

    def test_attack_a_parent_named_sudo_that_is_not_root(self) -> None:
        impostor = replace(SUDO, euid=ME, exe="/home/tester/bin/sudo")
        assert asking_sudo(table(SHELL, impostor, HELPER), HELPER.pid) is None

    def test_attack_a_root_parent_that_is_not_sudo(self) -> None:
        # Orphaned, the helper is adopted by init, which is root.
        init = Process(1, 0, "systemd", 0, 0, ("/usr/lib/systemd/systemd",), None)
        adopted = replace(HELPER, parent=1)
        assert asking_sudo(table(init, adopted), HELPER.pid) is None

    def test_attack_the_helper_run_as_root_as_sudos_command(self) -> None:
        as_root = replace(HELPER, uid=0, euid=0)
        assert asking_sudo(table(SHELL, SUDO, as_root), HELPER.pid) is None

    def test_attack_a_sudo_run_by_someone_else(self) -> None:
        theirs = replace(SUDO, uid=1001)
        assert asking_sudo(table(SHELL, theirs, HELPER), HELPER.pid) is None

    def test_a_helper_that_is_gone_has_no_parent(self) -> None:
        assert asking_sudo(table(SUDO), HELPER.pid) is None


class TestTheCommandSudoWasAskedToRun:
    @pytest.mark.parametrize(
        ("cmdline", "command", "user"),
        [
            (SUDO.cmdline, ("pacman", "-S", "cowsay"), "root"),
            (
                ("sudo", "-kAuhttp", "systemctl", "restart", "nginx"),
                ("systemctl", "restart", "nginx"),
                "http",
            ),
            (
                ("sudo", "--user=alice", "--chdir", "/tmp", "--", "ls", "-l"),
                ("ls", "-l"),
                "alice",
            ),
            (("sudo", "-u", "bob", "-E", "id"), ("id",), "bob"),
            (("sudo", "-p", "Password:", "-C", "5", "true"), ("true",), "root"),
            (
                ("sudo", "-A", "LD_PRELOAD=/tmp/x.so", "ls"),
                ("LD_PRELOAD=/tmp/x.so", "ls"),
                "root",
            ),
            (("sudo", "-A", "ls", "-u", "x"), ("ls", "-u", "x"), "root"),
            (("sudo", "-hhost", "-u", "eve", "ls"), ("ls",), "eve"),
        ],
    )
    def test_is_what_follows_sudos_own_options(
        self, cmdline: tuple[str, ...], command: tuple[str, ...], user: str
    ) -> None:
        request = request_of(cmdline)
        assert (request.command, request.user) == (command, user)
