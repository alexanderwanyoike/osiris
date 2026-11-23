"""The person's daily picture limit: none unless they set one."""

from __future__ import annotations

from pathlib import Path

from osiris.harness.media.limit_setting import (
    LIMIT_FILE,
    daily_limit,
    set_daily_limit,
)
from osiris.platform import FakeFileSystem

HOME = Path("/home/tester")


def test_there_is_no_limit_by_default() -> None:
    assert daily_limit(FakeFileSystem(), HOME) is None


def test_a_limit_the_person_sets_reads_back_as_plain_text() -> None:
    files = FakeFileSystem()

    set_daily_limit(files, HOME, 30)

    assert daily_limit(files, HOME) == 30
    assert files.read(HOME / LIMIT_FILE) == "30\n"


def test_removing_the_limit_leaves_none() -> None:
    files = FakeFileSystem()
    set_daily_limit(files, HOME, 30)

    set_daily_limit(files, HOME, None)

    assert daily_limit(files, HOME) is None
    assert not files.exists(HOME / LIMIT_FILE)
