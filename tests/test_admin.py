"""The admin password guards: who may ask for a password, for what, and where
the request is shown (ADR 0018)."""

from __future__ import annotations

import os
import shlex
import sys
from dataclasses import replace

import pytest

from osiris.harness.admin import (
    AGENT_SUDO_SCRIPT,
    HELPER_ARGV,
    HELPER_SCRIPT,
    Kind,
    NotTheAgents,
    Refuse,
    Show,
    agent_environment,
    asking_program,
    asking_sudo,
    caller_sudo,
    descends_from,
    judge,
    request_of,
)
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


class TestWhatKindOfCommandItIs:
    @pytest.mark.parametrize(
        "command",
        [
            ("pacman", "-S", "cowsay"),
            ("/usr/bin/systemctl", "restart", "sshd"),
            ("/usr/local/bin/tool",),
            ("LANG=C", "pacman", "-Syu"),
        ],
    )
    def test_a_system_command_is_shown_as_it_is(self, command: tuple[str, ...]) -> None:
        request = request_of(("sudo", "-A", *command))
        assert request.kind is Kind.COMMAND
        assert request.note is None

    @pytest.mark.parametrize(
        "command",
        [
            ("sh", "-c", "pacman -Syu && rm -rf /var/cache"),
            ("/usr/bin/bash", "-lc", "echo hi > /etc/motd"),
            ("zsh", "-e", "-c", "true"),
            ("FOO=1", "dash", "-c", "true"),
        ],
    )
    def test_a_shell_string_is_shown_in_full_and_labelled(
        self, command: tuple[str, ...]
    ) -> None:
        request = request_of(("sudo", "-A", *command))
        assert request.kind is Kind.SHELL
        assert request.shown == shlex.join(command)
        assert request.note == "A shell command, shown in full: all of it runs as root."

    @pytest.mark.parametrize(
        "command",
        [
            ("./install.sh",),
            ("/home/tester/Code/tool/setup", "--all"),
            ("bash", "install.sh"),
            ("python3", "-u", "/tmp/fix.py"),
        ],
    )
    def test_a_script_says_its_contents_are_not_shown(
        self, command: tuple[str, ...]
    ) -> None:
        request = request_of(("sudo", "-A", *command))
        assert request.kind is Kind.SCRIPT
        assert request.note == "Runs a script; its contents are not shown."

    def test_the_note_names_the_user_it_runs_as(self) -> None:
        request = request_of(("sudo", "-u", "http", "sh", "-c", "id"))
        assert request.note == "A shell command, shown in full: all of it runs as http."


class TestSudosOwnModes:
    @pytest.mark.parametrize("option", ["-s", "-i", "--shell", "--login"])
    def test_a_shell_with_no_command_is_an_interactive_shell(self, option: str) -> None:
        request = request_of(("sudo", "-A", option))
        assert request.kind is Kind.SHELL
        assert request.shown == "an interactive shell"

    def test_a_command_given_to_sudos_shell_runs_as_a_shell_string(self) -> None:
        request = request_of(("sudo", "-A", "-s", "pacman -Syu; reboot"))
        assert request.kind is Kind.SHELL
        assert request.shown == "'pacman -Syu; reboot'"

    @pytest.mark.parametrize(
        "cmdline",
        [
            ("sudo", "-A", "-e", "/etc/hosts"),
            ("sudo", "--edit", "/etc/hosts"),
            ("sudoedit", "/etc/hosts"),
        ],
    )
    def test_editing_is_shown_as_sudoedit(self, cmdline: tuple[str, ...]) -> None:
        request = request_of(cmdline)
        assert request.kind is Kind.COMMAND
        assert request.shown == "sudoedit /etc/hosts"

    def test_no_command_at_all_only_checks_the_password(self) -> None:
        assert request_of(("sudo", "-k", "-A", "-v")).shown == (
            "nothing: sudo only checks the password"
        )


class TestTheCallerTheHarnessAnswers:
    def test_is_the_helper_started_by_a_genuine_sudo(self) -> None:
        assert caller_sudo(genuine(), HELPER.pid, uid=ME) == SUDO

    def test_attack_a_fake_helper_calling_the_harness(self) -> None:
        # Its command line can be made to look like the helper's; its parent
        # cannot be made a root sudo.
        fake = replace(HELPER, parent=SHELL.pid)
        assert caller_sudo(table(SHELL, fake), HELPER.pid, uid=ME) is None

    def test_attack_sudo_askpass_pointing_at_another_program(self) -> None:
        other = replace(
            HELPER, cmdline=("/home/tester/steal", PROMPT), exe="/home/tester/steal"
        )
        assert caller_sudo(table(SHELL, SUDO, other), HELPER.pid, uid=ME) is None

    def test_attack_another_script_that_names_the_helper(self) -> None:
        script = replace(
            HELPER,
            cmdline=("/usr/bin/python3", "/tmp/steal.py", "/usr/lib/osiris/askpass"),
        )
        assert caller_sudo(table(SHELL, SUDO, script), HELPER.pid, uid=ME) is None

    def test_attack_another_interpreter_running_the_helpers_command_line(
        self,
    ) -> None:
        copied = replace(HELPER, exe="/home/tester/.local/bin/python3.14")
        assert caller_sudo(table(SHELL, SUDO, copied), HELPER.pid, uid=ME) is None

    def test_attack_a_helper_of_another_account(self) -> None:
        theirs = replace(SUDO, uid=1001)
        helper = replace(HELPER, uid=1001, euid=1001)
        assert caller_sudo(table(SHELL, theirs, helper), HELPER.pid, uid=ME) is None

    def test_attack_a_helper_whose_sudo_is_not_root(self) -> None:
        impostor = replace(SUDO, euid=ME)
        assert caller_sudo(table(SHELL, impostor, HELPER), HELPER.pid, uid=ME) is None


class TestWhetherTheSudoIsTheAgents:
    def test_a_sudo_the_engines_shell_started_is(self) -> None:
        assert descends_from(genuine(), SUDO.pid, ENGINE.pid)

    def test_attack_a_sudo_outside_the_engines_process_tree(self) -> None:
        terminal = Process(
            pid=80,
            parent=1,
            name="ghostty",
            uid=ME,
            euid=ME,
            cmdline=("ghostty",),
            exe="/usr/bin/ghostty",
        )
        zsh = replace(SHELL, pid=90, parent=80, name="zsh", cmdline=("zsh",))
        theirs = replace(SUDO, parent=90)
        processes = table(ENGINE, terminal, zsh, theirs)
        assert not descends_from(processes, SUDO.pid, ENGINE.pid)

    def test_with_no_engine_none_is(self) -> None:
        assert not descends_from(genuine(), SUDO.pid, None)

    def test_a_broken_chain_of_parents_ends_the_search(self) -> None:
        orphan = replace(SUDO, parent=999)
        assert not descends_from(table(ENGINE, orphan), SUDO.pid, ENGINE.pid)

    def test_a_process_is_not_its_own_descendant(self) -> None:
        assert not descends_from(genuine(), ENGINE.pid, ENGINE.pid)


COMMAND = ("pacman", "-S", "cowsay")


class TestWhatTheHarnessDoesWithARequest:
    def test_the_agents_sudo_is_shown_in_its_conversation(self) -> None:
        verdict = judge(
            genuine(), HELPER.pid, COMMAND, uid=ME, engine=ENGINE.pid, session="ses_1"
        )
        assert verdict == Show(request_of(SUDO.cmdline), "ses_1")

    def test_a_caller_that_is_not_the_helper_is_refused(self) -> None:
        fake = replace(HELPER, parent=SHELL.pid)
        verdict = judge(
            table(ENGINE, SHELL, fake),
            HELPER.pid,
            COMMAND,
            uid=ME,
            engine=ENGINE.pid,
            session="ses_1",
        )
        assert isinstance(verdict, Refuse)

    def test_attack_a_command_other_than_the_one_sudo_runs_is_refused(self) -> None:
        verdict = judge(
            genuine(),
            HELPER.pid,
            ("ls",),
            uid=ME,
            engine=ENGINE.pid,
            session="ses_1",
        )
        assert isinstance(verdict, Refuse)

    def test_a_sudo_outside_the_engine_is_not_the_agents(self) -> None:
        verdict = judge(
            genuine(), HELPER.pid, COMMAND, uid=ME, engine=999, session="ses_1"
        )
        assert verdict == NotTheAgents(request_of(SUDO.cmdline))

    def test_the_engines_sudo_with_no_conversation_running_it_is_not_the_agents(
        self,
    ) -> None:
        verdict = judge(
            genuine(), HELPER.pid, COMMAND, uid=ME, engine=ENGINE.pid, session=None
        )
        assert verdict == NotTheAgents(request_of(SUDO.cmdline))


class TestTheProgramThatAsked:
    def test_is_the_nearest_parent_that_is_not_a_shell(self) -> None:
        claude = replace(ENGINE, pid=60, name="node", cmdline=("claude",))
        zsh = replace(SHELL, pid=70, parent=60, name="zsh", cmdline=("/bin/zsh",))
        bash = replace(SHELL, parent=70)
        processes = table(claude, zsh, bash, SUDO)
        assert asking_program(processes, SUDO) == "claude"

    def test_is_named_by_its_command_or_else_by_the_kernel(self) -> None:
        nameless = replace(ENGINE, cmdline=())
        assert asking_program(table(nameless, SHELL, SUDO), SUDO) == "opencode"
        assert asking_program(genuine(), SUDO) == "opencode"

    def test_is_unknown_when_only_shells_are_left(self) -> None:
        assert asking_program(table(SHELL, SUDO), SUDO) == "an unknown program"

    def test_a_login_shell_is_a_shell_too(self) -> None:
        terminal = replace(ENGINE, name="ghostty", cmdline=("ghostty",))
        login = replace(SHELL, name="zsh", cmdline=("-zsh",))
        assert asking_program(table(terminal, login, SUDO), SUDO) == "ghostty"


class TestTheAgentsEnvironment:
    def test_puts_the_agents_sudo_first_and_names_the_helper(self) -> None:
        env = agent_environment({"PATH": "/usr/bin:/bin", "LANG": "C"})
        assert env == {
            "PATH": "/usr/lib/osiris/agent-bin:/usr/bin:/bin",
            "LANG": "C",
            "SUDO_ASKPASS": "/usr/lib/osiris/askpass",
        }

    def test_is_the_same_when_applied_twice(self) -> None:
        once = agent_environment({"PATH": "/usr/bin"})
        assert agent_environment(once) == once


class TestTheInstalledScripts:
    def test_the_agents_sudo_asks_every_time_through_the_helper(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run: list[tuple[str, list[str], dict[str, str]]] = []
        monkeypatch.setattr(
            os, "execve", lambda path, argv, env: run.append((path, argv, env))
        )
        monkeypatch.setattr(sys, "argv", ["sudo", "pacman", "-S", "cowsay"])
        monkeypatch.setenv("SUDO_ASKPASS", "/home/tester/steal")
        exec(compile(AGENT_SUDO_SCRIPT, "sudo", "exec"), {"__name__": "__main__"})
        [(path, argv, env)] = run
        assert path == "/usr/bin/sudo"
        assert argv == ["/usr/bin/sudo", "-k", "-A", "pacman", "-S", "cowsay"]
        assert env["SUDO_ASKPASS"] == "/usr/lib/osiris/askpass"

    def test_the_helper_runs_as_the_harness_checks_that_it_does(self) -> None:
        assert HELPER_SCRIPT.splitlines()[0] == "#!" + " ".join(HELPER_ARGV[:2])
