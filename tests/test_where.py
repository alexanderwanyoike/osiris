"""Where a Conversation runs (#169): its Project's folder and branch."""

from __future__ import annotations

from pathlib import Path

from osiris.harness.where import branch
from osiris.platform import FakeRunner
from osiris.platform.process import CommandError, Result

TIMER = Path("/home/tester/Code/timer")
ASK = f"git -C {TIMER} rev-parse --abbrev-ref HEAD"


def test_a_projects_branch_is_the_one_checked_out() -> None:
    runner = FakeRunner(results={ASK: Result((), 0, "main\n")})
    assert branch(runner, TIMER) == "main"


def test_a_folder_that_is_no_repository_has_no_branch() -> None:
    runner = FakeRunner(results={ASK: CommandError(ASK.split(), 128)})
    assert branch(runner, TIMER) == ""
