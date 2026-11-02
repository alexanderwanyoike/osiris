"""Osiris tools run from the catalogue show as steps from what the tool
server logged (#183)."""

from __future__ import annotations

from osiris.harness.engine import ToolFinished

from .test_side_by_side import app, asked, heard


def test_a_tool_the_server_ran_is_a_step_once_a_tool_finishes() -> None:
    stand_in, _engine = app()
    conversation = asked(stand_in, "make it calm")
    session = stand_in.harness.session or ""
    stand_in.log.write("ran", session=session, tool="osiris_apply_theme")
    heard(stand_in, ToolFinished(session, "c1", "applied"))
    assert [s.action for s in conversation.turns[-1].steps] == ["osiris_apply_theme"]
