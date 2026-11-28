"""The daily limit: a paid tool runs without a card, so this protects the credit."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from osiris.harness.media.error import MediaError
from osiris.harness.media.limit import DailyLimit
from osiris.platform import FakeFileSystem

USAGE = Path("/home/tester/.config/osiris/media/images")
MONDAY = date(2026, 11, 23)
TUESDAY = date(2026, 11, 24)


def limited(files: FakeFileSystem, day: date = MONDAY, images: int = 2) -> DailyLimit:
    return DailyLimit(files, USAGE, lambda: day, images=images)


def test_pictures_are_counted_up_to_the_limit_and_no_further() -> None:
    files = FakeFileSystem()
    limit = limited(files)

    limit.take()
    limit.take()
    with pytest.raises(MediaError, match=r"limit of 2 pictures.*Settings"):
        limit.take()

    assert files.read(USAGE).splitlines() == ["2026-11-23", "2026-11-23"]


def test_a_limit_of_one_is_worded_as_one_picture() -> None:
    files = FakeFileSystem()
    limited(files, images=1).take()

    with pytest.raises(MediaError, match=r"limit of 1 picture\."):
        limited(files, images=1).take()


def test_the_limit_starts_again_the_next_day() -> None:
    files = FakeFileSystem()
    limited(files, images=1).take()

    limited(files, TUESDAY, images=1).take()


def test_two_tool_servers_at_the_last_picture_cannot_both_spend_it() -> None:
    class Racing(FakeFileSystem):
        def append(self, path: Path, text: str) -> None:
            # The other tool server takes the last picture just before this one.
            super().append(path, text)
            super().append(path, text)

    with pytest.raises(MediaError, match="limit of 1 picture"):
        limited(Racing(), images=1).take()
