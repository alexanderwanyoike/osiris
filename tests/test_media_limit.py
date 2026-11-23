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
