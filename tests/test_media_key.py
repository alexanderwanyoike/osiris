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


def test_characters_a_terminal_or_paste_added_are_dropped() -> None:
    files = FakeFileSystem()

    media_key.save_fal_key(files, HOME, "\b\b a-key\x1b\n")

    assert media_key.fal_key(files, HOME) == "a-key"


def test_a_key_edited_by_hand_with_stray_characters_still_reads_clean() -> None:
    files = FakeFileSystem()
    files.write(KEY_PATH, "\b\ba-key\n", mode=0o600)

    assert media_key.fal_key(files, HOME) == "a-key"


def test_removing_the_key_disconnects_fal() -> None:
    files = FakeFileSystem()
    media_key.save_fal_key(files, HOME, "a-key")

    media_key.remove_fal_key(files, HOME)

    assert media_key.fal_key(files, HOME) is None
    assert not files.exists(KEY_PATH)
