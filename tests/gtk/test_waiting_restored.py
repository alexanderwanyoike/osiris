"""A request still waiting when the drawer restarts gets its card back (#182)."""

from __future__ import annotations

from types import SimpleNamespace

from osiris.harness.engine import ToolRequested

from .test_side_by_side import app, asked


def test_a_request_still_waiting_comes_back_as_its_card() -> None:
    stand_in, _engine = app()
    conversation = asked(stand_in, "list /etc")
    session = stand_in.harness.session or ""
    stand_in.requests = SimpleNamespace(
        waiting=lambda s: [ToolRequested(s, "per_1", "bash", ("ls /etc",))]
    )
    stand_in.restore_waiting(session)
    turn = conversation.turns[-1]
    assert turn.held is not None or turn.asking is not None
