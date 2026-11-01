"""What fills a Conversation's context window (#169).

The Engine reports how many tokens are in use, not what they are, so the
share of each kind is estimated from the size of the messages it keeps; the
panel says so.
"""

from __future__ import annotations

from dataclasses import dataclass

#: What fills a context window, in the order it is shown.
KINDS = ("instructions", "questions", "answers", "tools")


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


def grid(shared: list[Slice], squares: int) -> list[str]:
    """``squares`` small squares, each a slice of the window, in kind order.
    A kind with any tokens keeps a square, taken from the largest."""
    total = sum(s.tokens for s in shared) or 1
    exact = [s.tokens * squares / total for s in shared]
    counts = [int(share) for share in exact]
    # Squares left by rounding down go to the largest remainders.
    by_remainder = sorted(range(len(shared)), key=lambda i: counts[i] - exact[i])
    for i in by_remainder[: squares - sum(counts)]:
        counts[i] += 1
    for i, part in enumerate(shared):
        if part.tokens and not counts[i]:
            counts[counts.index(max(counts))] -= 1
            counts[i] = 1
    return [
        part.kind
        for part, count in zip(shared, counts, strict=True)
        for _ in range(count)
    ]
