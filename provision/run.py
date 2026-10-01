"""Process helpers.

Every command is an argv list handed straight to execve. Nothing in Osiris
shells out: no `bash -c`, no `shell=True`, no string interpolation into a
command line. Redirection is done in Python, not by a shell.

Output goes to stdout by default. The graphical installer calls set_sink() to
route it into its log view instead - a sink here rather than a redirect of
sys.stdout, because stream() hands its child a real file descriptor and a
redirected sys.stdout would not catch a word of it.
"""
import os
import pty
import re
import subprocess
import sys

_sink = None

# Colour and cursor-movement codes, which pacman emits once it believes it is
# talking to a terminal.
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")


def set_sink(sink) -> None:
    """Send command output to sink(line) instead of stdout. None restores it."""
    global _sink
    _sink = sink


def emit(line: str) -> None:
    if _sink is None:
        print(line, flush=True)
    else:
        _sink(line)


def run(*argv: str, check: bool = True, quiet: bool = False) -> str:
    """Run argv and return stdout."""
    if not quiet:
        emit("  $ " + " ".join(argv))
    result = subprocess.run(argv, check=check, text=True, capture_output=True)
    if result.stdout and not quiet:
        for line in result.stdout.strip().splitlines()[-1:]:
            emit(f"    {line}")
    return result.stdout


def stream(*argv: str) -> None:
    """Run argv with output going straight through (long installs).

    With a sink attached the child gets a pseudo-terminal rather than a pipe.
    That is not cosmetic: pacman checks whether its output is a terminal and
    block-buffers when it is not, so a pipe shows "Retrieving packages..." and
    then nothing at all for the fifteen minutes it takes to install a desktop.
    On a pty it reports progress as it goes.

    The cost is that it also starts emitting colour and cursor-movement codes,
    which are stripped here, and that progress updates arrive terminated by
    carriage returns - hence splitting on both.
    """
    emit("  $ " + " ".join(argv))
    if _sink is None:
        subprocess.run(argv, check=True)
        return

    master, slave = pty.openpty()
    try:
        process = subprocess.Popen(argv, stdout=slave, stderr=slave,
                                   stdin=subprocess.DEVNULL, close_fds=True)
    except BaseException:
        os.close(master)
        os.close(slave)
        raise
    os.close(slave)

    pending = ""
    try:
        while True:
            try:
                chunk = os.read(master, 8192)
            except OSError:
                # The child closed the other end; on Linux this is EIO, not EOF.
                break
            if not chunk:
                break
            pending += chunk.decode("utf-8", "replace")
            *lines, pending = re.split(r"[\r\n]", pending)
            for line in lines:
                line = ANSI.sub("", line).rstrip()
                if line:
                    emit("    " + line)
    finally:
        os.close(master)
    if pending.strip():
        emit("    " + ANSI.sub("", pending).rstrip())

    if process.wait() != 0:
        raise subprocess.CalledProcessError(process.returncode, argv)


def capture(*argv: str) -> str:
    """Run argv and return stripped stdout, printing nothing."""
    return subprocess.run(
        argv, check=True, text=True, capture_output=True
    ).stdout.strip()


def die(message: str) -> None:
    sys.exit(f"error: {message}")
