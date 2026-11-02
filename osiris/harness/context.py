"""What fills a Conversation's context window (#169).

The Engine reports how many tokens are in use, not what they are, so the
share of each kind is estimated from the size of the messages it keeps; the
panel says so.
"""

from __future__ import annotations

from dataclasses import dataclass

#: What fills a context window, in the order it is shown.
KINDS = ("instructions", "questions", "answers", "tools")


#: Characters to a token, near enough for an estimate.
CHARACTERS = 4


@dataclass(frozen=True)
class ContextUse:
    #: Each kind's estimated tokens.
    sizes: dict[str, int]
    #: Tokens in use, as the Engine reported them for its last step.
    used: int


@dataclass(frozen=True)
class Slice:
    kind: str
    tokens: int


def slices(sizes: dict[str, int], used: int, window: int) -> list[Slice]:
    """``used`` tokens shared out by ``sizes``, each kind's estimated tokens,
    then what is free of ``window``. What the messages do not account for is
    the Engine's own instructions, its prompt and tool catalogue."""
    estimated = sum(sizes.get(kind, 0) for kind in KINDS)
    scale = used / estimated if estimated > used else 1.0
    shares = {kind: round(sizes.get(kind, 0) * scale) for kind in KINDS}
    shares["instructions"] += used - sum(shares.values())
    return [
        *(Slice(kind, shares[kind]) for kind in KINDS),
        Slice("free", max(window - used, 0)),
    ]


#: How full the window is when its ring starts to turn to the danger colour,
#: and when it has: well before full, while there is time to start afresh.
WARM = 0.6
FULL = 0.95


def filled(used: int, window: int) -> float:
    """How much of ``window`` is in use, as a share of it."""
    return min(used / window, 1.0) if window else 0.0


def alarm(used: int, window: int) -> float:
    """How far the ring has turned from the accent to the danger colour."""
    return min(max((filled(used, window) - WARM) / (FULL - WARM), 0.0), 1.0)
