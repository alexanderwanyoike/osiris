"""The Programs' history as crediting shell commits reads it."""

from __future__ import annotations

from pathlib import Path

from program_history import ProgramHistory

from osiris.platform import FakeFileSystem, FakeRunner
from osiris.platform.process import Result
from osiris.programs.manifest import MANIFEST_FILE
from osiris.programs.programs import Programs

HOME = Path("/home/tester")


def test_a_program_whose_history_cannot_be_read_has_nothing_rewritten() -> None:
    """Unreadable is not rewritten: a Program that is gone keeps its record."""
    files = FakeFileSystem()
    files.write(HOME / "Code" / "pomodoro" / MANIFEST_FILE, "{}")
    runner = FakeRunner(results={"git": Result((), 128, "")})
    history = ProgramHistory(Programs(files, runner, HOME))
    assert history.rewritten("pomodoro", ["abc123"]) == []
