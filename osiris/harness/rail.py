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


def placed(tops: list[float], height: float) -> list[float]:
    """Where each question starts, as a share of the Conversation's height."""
    return [top / height if height else 0.0 for top in tops]


def on_screen(tops: list[float], total: float, top: float, height: float) -> list[bool]:
    """Whether any of each question, or the answer under it, is scrolled into
    the view ``height`` tall from ``top``: it runs from where it starts to
    where the next one does."""
    ends = [*tops[1:], total]
    return [
        start < top + height and end > top
        for start, end in zip(tops, ends, strict=True)
    ]
