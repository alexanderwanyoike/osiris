"""A drifting wallpaper's loop: which frame is due, and what to render first."""

import pytest

from osiris.themes.frames import due, render_order


def test_the_loop_starts_at_frame_zero() -> None:
    assert due(0, loop=600, count=120) == (0, 0.0)


def test_partway_between_frames_is_a_blend_into_the_next() -> None:
    index, amount = due(7.5, loop=600, count=120)
    assert index == 1
    assert amount == pytest.approx(0.5)


def test_the_last_frame_blends_back_into_the_first() -> None:
    index, amount = due(599, loop=600, count=120)
    assert index == 119
    assert amount == pytest.approx(0.8)
    assert due(600, loop=600, count=120) == (0, 0.0)


def test_the_clock_carries_on_across_loops() -> None:
    assert due(600 * 1000 + 10, loop=600, count=120) == due(10, loop=600, count=120)


def test_render_order_starts_with_the_frame_due_and_wraps() -> None:
    order = render_order(590, loop=600, count=120)
    assert order[:4] == [118, 119, 0, 1]
    assert sorted(order) == list(range(120))
