"""The process port.

These are the tests that justify the seam existing: everything below is about
behaviour that used to need a virtual machine to observe.
"""

from __future__ import annotations

import pytest

from osiris.platform import CommandError, CommandRunner, FakeRunner, SubprocessRunner
from osiris.platform.process import Result


class TestFakeRunner:
    def test_records_what_it_was_asked_to_run(self) -> None:
        runner = FakeRunner()
        runner.run("pacman", "-S", "cinnamon")
        assert runner.commands == ["pacman -S cinnamon"]
        assert runner.ran("pacman", "-S")
        assert not runner.ran("pacman", "-R")

    def test_unplanned_commands_succeed(self) -> None:
        assert FakeRunner().run("anything").ok

    def test_a_planned_failure_raises(self) -> None:
        runner = FakeRunner(results={"pacstrap": Result(("pacstrap",), 1)})
        with pytest.raises(CommandError) as caught:
            runner.stream("pacstrap", "-K", "/mnt")
        assert caught.value.returncode == 1

    def test_check_false_returns_the_failure_instead_of_raising(self) -> None:
        runner = FakeRunner(results={"grub-install": Result(("x",), 2)})
        assert runner.run("grub-install", check=False).returncode == 2

    def test_a_whole_command_line_beats_a_bare_program(self) -> None:
        runner = FakeRunner(
            results={
                "blkid": Result(("blkid",), 0, "wrong\n"),
                "blkid -s UUID": Result(("blkid",), 0, "right\n"),
            }
        )
        assert runner.capture("blkid", "-s", "UUID") == "right"

    def test_counts_and_arguments_are_available_to_assertions(self) -> None:
        runner = FakeRunner()
        runner.run("grub-install", "--removable")
        runner.run("grub-install", "--bootloader-id=Osiris")
        assert runner.count("grub-install") == 2
        assert ("grub-install", "--removable") in runner.arguments_to("grub-install")


class TestSubprocessRunner:
    def test_satisfies_the_port(self) -> None:
        assert isinstance(SubprocessRunner(), CommandRunner)
        assert isinstance(FakeRunner(), CommandRunner)

    def test_capture_returns_stripped_stdout(self) -> None:
        assert SubprocessRunner().capture("echo", "  hello  ") == "hello"

    def test_a_failure_carries_the_command_and_code(self) -> None:
        with pytest.raises(CommandError) as caught:
            SubprocessRunner().run("false", quiet=True)
        assert caught.value.returncode == 1
        assert caught.value.argv == ["false"]

    def test_arguments_are_never_interpreted_by_a_shell(self) -> None:
        """The whole point of argv-only execution.

        If this went through a shell, the semicolon would start a second
        command and the backtick would substitute. It comes back as a literal.
        """
        hostile = "; touch /tmp/osiris-pwned; echo `whoami`"
        assert SubprocessRunner().capture("echo", hostile) == hostile

    def test_streaming_forwards_lines_to_the_sink(self) -> None:
        lines: list[str] = []
        runner = SubprocessRunner(sink=lines.append)
        runner.stream("printf", "one\\ntwo\\n")
        assert "    one" in lines
        assert "    two" in lines

    def test_streaming_splits_on_carriage_returns(self) -> None:
        """Progress written with \\r has to arrive, not sit in a buffer.

        This is the behaviour that stops a fifteen-minute pacstrap looking
        like a hung installer.
        """
        lines: list[str] = []
        runner = SubprocessRunner(sink=lines.append)
        runner.stream("printf", "10%%\\r50%%\\r100%%\\n")
        # Output lines carry a four-space prefix; the echoed command does not.
        output = [line.strip() for line in lines if line.startswith("    ")]
        assert output == ["10%", "50%", "100%"]

    def test_streaming_strips_terminal_escape_codes(self) -> None:
        lines: list[str] = []
        runner = SubprocessRunner(sink=lines.append)
        runner.stream("printf", "\\033[32mgreen\\033[0m\\n")
        assert "    green" in lines

    def test_a_streamed_failure_raises(self) -> None:
        with pytest.raises(CommandError):
            SubprocessRunner(sink=lambda _line: None).stream("false")
