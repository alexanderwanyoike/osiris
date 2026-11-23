"""The person's daily picture limit: none unless they set one."""

from __future__ import annotations

from pathlib import Path

import pytest

from osiris.harness.media.limit_setting import (
    LIMIT_FILE,
    daily_limit,
    set_daily_limit,
)
from osiris.platform import FakeFileSystem, RealFileSystem

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


@pytest.mark.parametrize("written", ["", "twenty", "-5", "2.5", "9" * 5000])
def test_a_limit_mistyped_by_hand_stops_spending_rather_than_lifting_it(
    written: str,
) -> None:
    files = FakeFileSystem()
    files.write(HOME / LIMIT_FILE, written)

    assert daily_limit(files, HOME) == 0


def test_a_limit_file_that_is_not_text_stops_spending(tmp_path: Path) -> None:
    path = tmp_path / LIMIT_FILE
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\xff\xfe")

    assert daily_limit(RealFileSystem(), tmp_path) == 0


def test_a_limit_path_that_cannot_be_read_stops_spending(tmp_path: Path) -> None:
    (tmp_path / LIMIT_FILE).mkdir(parents=True)

    assert daily_limit(RealFileSystem(), tmp_path) == 0
