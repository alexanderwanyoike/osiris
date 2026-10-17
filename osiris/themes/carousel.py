"""The theme switcher's carousel, without the drawing.

The switcher shows the library as a ring of cards: the focused theme large in
the middle, its neighbours smaller and fainter either side. Browsing animates
a fractional position, so every card's place is a function of its distance
from that position, and the distance is taken round the ring so the last
theme sits beside the first.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise

from osiris.themes.library import Theme


@dataclass(frozen=True)
class Slot:
    #: Horizontal centre, in centre-card widths from the middle.
    x: float
    scale: float
    opacity: float


#: (distance, x, scale, opacity) at whole distances; between them, linear.
#: Each card tucks a little behind the one nearer the middle, which is what
#: makes the row read as one ring rather than a list of separate tiles.
NODES = (
    (0.0, 0.0, 1.0, 1.0),
    (1.0, 0.80, 0.70, 0.55),
    (2.0, 1.36, 0.50, 0.22),
    (3.0, 1.76, 0.38, 0.0),
)


def sequence(sections: Iterable[tuple[str, list[Theme]]]) -> list[tuple[str, Theme]]:
    """The arranged library as one row, each theme with its section's title."""
    return [(title, theme) for title, themes in sections for theme in themes]


def offset(index: int, position: float, count: int) -> float:
    """How far card `index` is from `position`, the short way round."""
    if count <= 1:
        return 0.0
    half = count / 2
    return (index - position + half) % count - half


def slot(distance: float) -> Slot:
    """Where a card `distance` from the middle sits, and how it looks."""
    reach = abs(distance)
    side = -1.0 if distance < 0 else 1.0
    for (d0, x0, s0, o0), (d1, x1, s1, o1) in pairwise(NODES):
        if reach <= d1:
            t = (reach - d0) / (d1 - d0)
            return Slot(
                x=side * (x0 + (x1 - x0) * t),
                scale=s0 + (s1 - s0) * t,
                opacity=o0 + (o1 - o0) * t,
            )
    d, x, s, _ = NODES[-1]
    return Slot(x=side * (x + (reach - d) * 0.4), scale=s, opacity=0.0)
