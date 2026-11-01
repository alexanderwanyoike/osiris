"""The Conversation rail (#167): a tick per question along the Conversation's
edge, for its length and the part on screen at a glance."""

from __future__ import annotations

from dataclasses import dataclass

from osiris.harness.conversation import Turn
from osiris.harness.titles import title_of


@dataclass(frozen=True)
class Tick:
    #: Where its question starts, as a share of the Conversation's height.
    at: float
    #: Whether any of it is on screen.
    lit: bool
    tone: str
    #: The start of its question, shown on hover.
    label: str
    #: The first question on screen, whose tick stands out.
    current: bool = False


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


def ticks(
    turns: list[Turn], tops: list[float], total: float, top: float, height: float
) -> list[Tick]:
    """A tick for each question, from where each starts in a Conversation
    ``total`` tall, scrolled to show ``height`` from ``top``."""
    seen = on_screen(tops, total, top, height)
    first = seen.index(True) if True in seen else -1
    return [
        Tick(at, lit, tone_of(turn), title_of(turn.question), index == first)
        for index, (turn, at, lit) in enumerate(
            zip(turns, placed(tops, total), seen, strict=True)
        )
    ]
