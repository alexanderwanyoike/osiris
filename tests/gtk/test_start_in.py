"""An Entry point into a folder: another app opens the Harness on a new
Conversation whose Project is that folder, as Appearance does for a Skin."""

from __future__ import annotations

from pathlib import Path

from tests.test_harness import HOME

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


def test_a_folder_entry_point_may_bring_a_request_left_unsent(tmp_path: Path) -> None:
    """Nothing reaches a model that the person has not seen: the request waits
    in the input until they send it."""
    stand_in, _ = app()
    stand_in.start_in(tmp_path, "Convert this theme to my Theme's colours")
    assert stand_in.drawer.drafts == ["Convert this theme to my Theme's colours"]
    assert stand_in.harness.session is None


def test_a_folder_given_before_the_harness_is_built_waits_for_it(
    tmp_path: Path,
) -> None:
    """D-Bus starts the Harness for the Entry point, and the Engine connection
    comes up after the action has arrived."""
    stand_in, _ = app()
    harness, stand_in.harness = stand_in.harness, None
    stand_in.start_in(tmp_path, "make it calm")
    stand_in.harness = harness
    stand_in.start_waiting()
    assert harness.directory == tmp_path
    assert stand_in.drawer.drafts == ["make it calm"]


def test_an_entry_point_into_anything_but_a_folder_is_ignored(tmp_path: Path) -> None:
    """Any program on the session bus can call it, and a Project is a folder."""
    stand_in, _ = app()
    (tmp_path / "a-file").write_text("")
    for given in (Path("relative"), tmp_path / "missing", tmp_path / "a-file"):
        stand_in.start_in(given, "make it calm")
    assert stand_in.harness.directory == HOME
    assert stand_in.drawer.drafts == []
