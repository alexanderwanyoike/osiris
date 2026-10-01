# 2. Python, and argv-only process execution

**Status:** Accepted

## Context

Osiris v1 was built with bash hooks running inside a chroot inside a 30-60
minute Docker build. A failure produced a non-zero exit code somewhere in a
pipeline, no stack trace, no local variables, and no way to re-run the failing
step without the preceding hour. That cost more development time than every
other problem in v1 combined, and was the reason v1 was abandoned.

The underlying problem is not that bash is a bad language. It is that bash
offers no way to observe a failure after the fact, and that a shell parses
every command line it is given - so a value containing a space, a semicolon or
a backtick changes the structure of the command rather than its argument.

## Decision

Build, install, provisioning and glue are written in Python.

Every external program is invoked as an **argv sequence** handed to `execve`.
No `shell=True`, no `bash -c`, no `os.system`, no string interpolation into a
command line. Redirection is done in Python.

Shell is permitted in exactly two places:

- The user's interactive shell configuration (`/etc/skel/.zshrc`), which is
  shell by definition.
- Files a third-party tool requires in shell syntax. `profiledef.sh`, which
  archiso demands, contains only variable assignments and is **generated** by
  `iso/profile.py`. The artefact is bash; the source is not.

## Consequences

Failures raise exceptions with tracebacks, and the failing step can be re-run
on its own.

Arguments are never re-parsed, so a path with a space, a password with a
semicolon or a hostname with a backtick is passed through unchanged. There is
no command injection surface because there is no command line to inject into.
This is asserted directly in `tests/test_process.py`.

The cost is verbosity: `run("mount", "-o", f"subvol=@,{options}", device, "/mnt")`
is longer than the shell equivalent. That is the trade, and it is accepted.

A second cost, discovered later: a program given a pipe instead of a terminal
may block-buffer its output. pacman does, and prints nothing for fifteen
minutes during a package install. `SubprocessRunner.stream` therefore gives
long-running commands a pseudo-terminal. See ADR 0003 for where that lives.
