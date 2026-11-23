"""The person's FAL key, kept in a file only they can read."""

from __future__ import annotations

from pathlib import Path

from osiris.harness.media import key as media_key
from osiris.platform import FakeFileSystem

HOME = Path("/home/tester")
KEY_PATH = HOME / ".config/osiris/media/fal-key"


def test_without_a_saved_key_fal_is_not_connected() -> None:
    assert media_key.fal_key(FakeFileSystem(), HOME) is None


def test_a_saved_key_reads_back_and_only_its_owner_can_read_it() -> None:
    files = FakeFileSystem()

    media_key.save_fal_key(files, HOME, "a-key")

    assert media_key.fal_key(files, HOME) == "a-key"
    assert files.modes[KEY_PATH] == 0o600
