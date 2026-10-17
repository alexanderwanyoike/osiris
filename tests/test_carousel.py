"""The theme switcher's carousel: its order, its ring and where cards sit."""

from itertools import pairwise

import pytest

from osiris.themes.carousel import Slot, offset, sequence, slot


def theme(name: str) -> dict:
    return {"name": name, "label": name.title()}


def test_sequence_keeps_sections_in_order() -> None:
    sections = [
        ("Favourites", [theme("ember")]),
        ("Blues", [theme("harbor"), theme("nord")]),
    ]
    assert [(title, t["name"]) for title, t in sequence(sections)] == [
        ("Favourites", "ember"),
        ("Blues", "harbor"),
        ("Blues", "nord"),
    ]


def test_offset_takes_the_short_way_round_the_ring() -> None:
    assert offset(0, 9, 10) == 1
    assert offset(9, 0, 10) == -1
    assert offset(3, 3.5, 10) == -0.5
    assert offset(5, 5, 10) == 0


def test_offset_of_a_single_theme_is_always_centre() -> None:
    assert offset(0, 0.4, 1) == 0


def test_the_centre_card_is_whole() -> None:
    assert slot(0) == Slot(x=0.0, scale=1.0, opacity=1.0)


def test_cards_mirror_either_side() -> None:
    for o in (0.3, 1, 1.7, 2.5):
        left, right = slot(-o), slot(o)
        assert left.x == -right.x
        assert (left.scale, left.opacity) == (right.scale, right.opacity)


def test_cards_shrink_and_fade_away_from_the_centre() -> None:
    steps = [slot(o / 4) for o in range(13)]
    for near, far in pairwise(steps):
        assert far.x > near.x
        assert far.scale < near.scale
        assert far.opacity <= near.opacity
    assert slot(3).opacity == 0
    assert slot(7).opacity == 0


@pytest.mark.parametrize("node", [1.0, 2.0])
def test_cards_move_smoothly_through_each_position(node: float) -> None:
    before, after = slot(node - 1e-6), slot(node + 1e-6)
    assert before.x == pytest.approx(after.x, abs=1e-4)
    assert before.scale == pytest.approx(after.scale, abs=1e-4)
