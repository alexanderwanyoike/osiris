"""The daily limit: a paid tool runs without a card, so this protects the credit."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pytest

from osiris.harness.media.error import MediaError
from osiris.harness.media.limit import DailyLimit
from osiris.platform import FakeFileSystem

USAGE = Path("/home/tester/.config/osiris/media/images")
MONDAY = date(2026, 11, 23)
TUESDAY = date(2026, 11, 24)


@dataclass
class Maker:
    failure: Exception | None = None
    asked: list[str] = field(default_factory=list)

    def make(self, description: str) -> bytes:
        self.asked.append(description)
        if self.failure is not None:
            raise self.failure
        return b"a picture"


def limited(
    maker: Maker, files: FakeFileSystem, day: date = MONDAY, images: int = 2
) -> DailyLimit:
    return DailyLimit(maker, files, USAGE, lambda: day, images=images)


def test_pictures_are_made_up_to_the_limit_and_no_further() -> None:
    maker, files = Maker(), FakeFileSystem()
    limit = limited(maker, files)

    assert limit.make("one") == b"a picture"
    assert limit.make("two") == b"a picture"
    with pytest.raises(MediaError, match="limit of 2 pictures"):
        limit.make("three")

    assert maker.asked == ["one", "two"]


def test_a_failed_request_still_counts_because_it_may_have_been_billed() -> None:
    files = FakeFileSystem()
    failing = limited(Maker(failure=MediaError("no")), files, images=1)
    with pytest.raises(MediaError, match="no"):
        failing.make("one")

    maker = Maker()
    with pytest.raises(MediaError, match="limit of 1 picture"):
        limited(maker, files, images=1).make("two")

    assert maker.asked == []


def test_a_limit_of_one_is_worded_as_one_picture() -> None:
    files = FakeFileSystem()
    limited(Maker(), files, images=1).make("one")

    with pytest.raises(MediaError, match=r"limit of 1 picture\."):
        limited(Maker(), files, images=1).make("two")


def test_the_limit_starts_again_the_next_day() -> None:
    files = FakeFileSystem()
    limited(Maker(), files, images=1).make("monday")

    assert limited(Maker(), files, TUESDAY, images=1).make("tuesday") == b"a picture"


def test_two_tool_servers_at_the_last_picture_cannot_both_spend_it() -> None:
    class Racing(FakeFileSystem):
        def append(self, path: Path, text: str) -> None:
            # The other tool server takes the last picture just before this one.
            super().append(path, text)
            super().append(path, text)

    maker, files = Maker(), Racing()

    with pytest.raises(MediaError, match="limit of 1 picture"):
        limited(maker, files, images=1).make("one")

    assert maker.asked == []
