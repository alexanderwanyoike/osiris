"""An Entry point into a folder: another app opens the Harness on a new
Conversation whose Project is that folder, as Appearance does for a Skin."""

from __future__ import annotations

from pathlib import Path

from .test_side_by_side import app, asked


def test_starting_in_a_folder_opens_a_new_conversation_there(tmp_path: Path) -> None:
    stand_in, _ = app()
    asked(stand_in, "make it calm")
    stand_in.start_in(tmp_path)
    assert stand_in.harness.directory == tmp_path
    assert stand_in.harness.session is None


def test_starting_in_a_folder_brings_the_drawer_out(tmp_path: Path) -> None:
    stand_in, _ = app()
    stand_in.open = False
    stand_in.unread_sessions = frozenset()
    stand_in.start_in(tmp_path)
    assert stand_in.open is True
