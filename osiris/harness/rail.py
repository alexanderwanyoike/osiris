"""The Conversation rail (#167): a tick per question along the Conversation's
edge, for its length and the part on screen at a glance."""

from __future__ import annotations

from osiris.harness.conversation import Turn


def tone_of(turn: Turn) -> str:
    """A tick's tint: "waiting" while the answer waits on the person,
    "changed" once it changed something, else "plain"."""
    if turn.asking or turn.held or turn.admin:
        return "waiting"
    if turn.changes:
        return "changed"
    return "plain"
