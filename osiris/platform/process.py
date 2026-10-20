"""Running other programs.

Every process Osiris starts goes through here, as an argv sequence handed
straight to execve. There is no shell anywhere in this project: no
``shell=True``, no ``bash -c``, and nothing interpolated into a command line,
so nothing can be quoted wrongly or injected into.

``CommandRunner`` is the port. ``SubprocessRunner`` is the real adapter;
``FakeRunner`` records calls and replays canned results, which is what makes
the install flow testable without a disk to ruin.
"""

from __future__ import annotations

import os
import pty
import re
import subprocess
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# Colour and cursor-movement codes, which pacman emits once it believes it is
# talking to a terminal.
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")

Sink = Callable[[str], None]


class CommandError(RuntimeError):
    """A command exited non-zero."""

    def __init__(self, argv: Sequence[str], returncode: int, output: str = "") -> None:
        self.argv = list(argv)
        self.returncode = returncode
        self.output = output
        detail = f": {output.strip()[-400:]}" if output.strip() else ""
        super().__init__(f"{' '.join(self.argv)} exited {returncode}{detail}")


@dataclass(frozen=True)
class Result:
    argv: tuple[str, ...]
    returncode: int
    stdout: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@runtime_checkable
class CommandRunner(Protocol):
    """Somewhere to send a command. The seam the whole codebase depends on."""

    def run(self, *argv: str, check: bool = True, quiet: bool = False) -> Result:
        """Run to completion and capture stdout."""
        ...

    def stream(
        self, *argv: str, check: bool = True, on_line: Sink | None = None
    ) -> Result:
        """Run with output forwarded as it arrives, and each line to on_line."""
        ...

    def capture(self, *argv: str) -> str:
        """Run and return stripped stdout, emitting nothing."""
        ...


@dataclass
class RecordedCall:
    argv: tuple[str, ...]
    streamed: bool = False


class SubprocessRunner:
    """The real one."""

    def __init__(self, sink: Sink | None = None) -> None:
        self._sink = sink

    def emit(self, line: str) -> None:
        if self._sink is None:
            print(line, flush=True)
        else:
            self._sink(line)

    def run(self, *argv: str, check: bool = True, quiet: bool = False) -> Result:
        if not quiet:
            self.emit("  $ " + " ".join(argv))
        completed = subprocess.run(argv, check=False, text=True, capture_output=True)
        if not quiet and completed.stdout.strip():
            for line in completed.stdout.strip().splitlines()[-1:]:
                self.emit(f"    {line}")
        if check and completed.returncode != 0:
            raise CommandError(
                argv, completed.returncode, completed.stderr or completed.stdout
            )
        return Result(tuple(argv), completed.returncode, completed.stdout)

    def stream(
        self, *argv: str, check: bool = True, on_line: Sink | None = None
    ) -> Result:
        """Run with output forwarded to the sink as it arrives.

        With a sink attached the child is given a pseudo-terminal rather than a
        pipe. That is not cosmetic: pacman checks whether its output is a
        terminal and block-buffers when it is not, so through a pipe it prints
        "Retrieving packages..." and then nothing at all for the fifteen
        minutes it takes to install a desktop.

        With a sink or an on_line, the lines forwarded come back as the
        result's stdout, and on_line hears each one, unprefixed, as it
        arrives. With neither the child writes straight to this terminal and
        there is nothing to return.
        """
        self.emit("  $ " + " ".join(argv))
        if self._sink is None and on_line is None:
            returncode, output = self._run_inheriting(argv), ""
        else:
            returncode, output = self._run_on_pty(argv, on_line)
        if check and returncode != 0:
            raise CommandError(argv, returncode)
        return Result(tuple(argv), returncode, output)

    def capture(self, *argv: str) -> str:
        completed = subprocess.run(argv, check=False, text=True, capture_output=True)
        if completed.returncode != 0:
            raise CommandError(argv, completed.returncode, completed.stderr)
        return completed.stdout.strip()

    # ---- the pty plumbing, kept out of stream() so each part stays legible --

    @staticmethod
    def _run_inheriting(argv: Sequence[str]) -> int:
        return subprocess.run(argv, check=False).returncode

    def _run_on_pty(self, argv: Sequence[str], on_line: Sink | None) -> tuple[int, str]:
        master, slave = pty.openpty()
        try:
            process = subprocess.Popen(
                argv,
                stdout=slave,
                stderr=slave,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
        except BaseException:
            os.close(master)
            os.close(slave)
            raise
        os.close(slave)
        forwarded: list[str] = []
        try:
            for line in self._read_lines(master):
                text = _ANSI.sub("", line).rstrip()
                if text:
                    self.emit("    " + text)
                    forwarded.append(text)
                    if on_line is not None:
                        on_line(text)
        finally:
            os.close(master)
        return process.wait(), "".join(f"{text}\n" for text in forwarded)

    @staticmethod
    def _read_lines(master: int) -> Iterator[str]:
        """Yield lines from a pty master until the child closes its end.

        Split on carriage returns as well as newlines: a program that believes
        it is on a terminal reports progress by returning to the start of the
        line rather than starting a new one.
        """
        pending = ""
        while True:
            try:
                chunk = os.read(master, 8192)
            except OSError:
                # The child closed its end; on Linux that is EIO, not EOF.
                break
            if not chunk:
                break
            pending += chunk.decode("utf-8", "replace")
            *complete, pending = re.split(r"[\r\n]", pending)
            yield from complete
        if pending:
            yield pending


@dataclass
class FakeRunner:
    """Records what was asked for and replays what you told it to.

    ``results`` maps the first word of a command - or the whole command line -
    to a Result or an exception to raise. Anything not mentioned succeeds
    silently, so a test only describes the calls it actually cares about.
    """

    results: dict[str, Result | Exception] = field(default_factory=dict)
    calls: list[RecordedCall] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)

    def emit(self, line: str) -> None:
        self.lines.append(line)

    def run(self, *argv: str, check: bool = True, quiet: bool = False) -> Result:
        if not quiet:
            self.emit("  $ " + " ".join(argv))
        return self._answer(argv, check, streamed=False)

    def stream(self, *argv: str, check: bool = True) -> Result:
        return self._answer(argv, check, streamed=True)

    def capture(self, *argv: str) -> str:
        return self._answer(argv, check=True, streamed=False).stdout.strip()

    def _answer(self, argv: Sequence[str], check: bool, streamed: bool) -> Result:
        self.calls.append(RecordedCall(tuple(argv), streamed))
        planned = self._lookup(argv)
        if isinstance(planned, Exception):
            raise planned
        result = planned or Result(tuple(argv), 0)
        if check and not result.ok:
            raise CommandError(argv, result.returncode, result.stdout)
        return result

    def _lookup(self, argv: Sequence[str]) -> Result | Exception | None:
        for key in (" ".join(argv), argv[0]):
            if key in self.results:
                return self.results[key]
        return None

    # ---- assertions, so tests read as sentences ----------------------------

    @property
    def commands(self) -> list[str]:
        return [" ".join(call.argv) for call in self.calls]

    def ran(self, *prefix: str) -> bool:
        return any(call.argv[: len(prefix)] == prefix for call in self.calls)

    def count(self, program: str) -> int:
        return sum(1 for call in self.calls if call.argv[0] == program)

    def arguments_to(self, program: str) -> list[tuple[str, ...]]:
        return [call.argv for call in self.calls if call.argv[0] == program]
