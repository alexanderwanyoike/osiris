"""Where the Conversation's widgets go (#169), by the room there is: never
over the messages, only expanded, and as wide as a share of the
Conversation. The Canvas open beside it only takes room."""

from __future__ import annotations

import pytest

from osiris.harness.widgets_place import LEAST, MOST, SHARE, place


@pytest.mark.parametrize(
    ("width", "where"),
    [
        # Room left of the centred messages.
        (1600, "float"),
        # Narrower: the messages move over to make a column for the cards.
        (1000, "beside"),
        # Shrunk: no room, so none.
        (540, "hidden"),
    ],
)
def test_the_widgets_go_where_there_is_room_for_them(width: int, where: str) -> None:
    assert place(width, readable=820, expanded=True)[0] == where


def test_the_drawer_shows_no_widgets() -> None:
    assert place(1600, readable=820, expanded=False)[0] == "hidden"


def test_a_card_is_a_share_of_the_conversations_width() -> None:
    assert place(1200, readable=820, expanded=True)[1] == round(1200 * SHARE)


def test_a_card_is_never_too_narrow_to_read_nor_wider_than_it_needs() -> None:
    assert place(500, readable=820, expanded=True)[1] == LEAST
    assert place(4000, readable=820, expanded=True)[1] == MOST


def test_a_card_is_never_reckoned_narrower_than_it_can_draw() -> None:
    """Room is kept for the card as drawn, so it never covers the messages."""
    where, card = place(1000, readable=820, expanded=True, least=280)
    assert card == 280
    assert where == "beside"
