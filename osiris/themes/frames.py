"""Which frame of a drifting wallpaper's loop is due, and what to render first.

A drifting wallpaper is a loop of frames played by the clock: frame `index` is
on screen, blending into the next by `amount`, and the last blends back into
the first. The clock rather than a counter, so the loop carries on across
logins and every process that asks agrees. The drift@osiris extension plays
the loop with the same arithmetic.
"""

from __future__ import annotations


def due(now: float, loop: float, count: int) -> tuple[int, float]:
    """The frame on screen at `now`, and how far it has blended into the next."""
    position = (now % loop) / loop * count
    index = int(position)
    return index, position - index


def render_order(now: float, loop: float, count: int) -> list[int]:
    """Every frame, starting with the one due now and on round the loop.

    Rendering is quicker than playback, so in this order the loop can start
    playing as soon as its first two frames exist and never catches up.
    """
    first, _ = due(now, loop, count)
    return [(first + step) % count for step in range(count)]
