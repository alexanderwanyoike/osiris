"""Where a Conversation runs (#169): its Project's folder and branch."""

from __future__ import annotations

from pathlib import Path

from osiris.platform import CommandRunner
from osiris.platform.process import CommandError


def branch(runner: CommandRunner, folder: Path) -> str:
    """The branch checked out in ``folder``, or nothing if it is no repository."""
    try:
        return runner.capture(
            "git", "-C", str(folder), "rev-parse", "--abbrev-ref", "HEAD"
        )
    except CommandError:
        return ""
