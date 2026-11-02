"""Where the Conversation's widgets go (#169), by the room there is: never
over the messages, and as wide as a share of the Conversation."""

from __future__ import annotations

import pytest

from osiris.harness.widgets_place import LEAST, MOST, SHARE, place


@pytest.mark.parametrize(
    ("width", "where"),
    [
        # Expanded, nothing beside it: room left of the centred messages.
        (1600, "float"),
        # Narrower: the messages move over to make a column for the cards.
        (1000, "beside"),
        # The drawer, or the Canvas open: no room, so a dropdown.
        (540, "dropdown"),
        (400, "dropdown"),
    ],
)
def test_the_widgets_go_where_there_is_room_for_them(width: int, where: str) -> None:
    assert place(width, readable=820)[0] == where


def test_a_card_is_a_share_of_the_conversations_width() -> None:
    assert place(1200, readable=820)[1] == round(1200 * SHARE)


def test_a_card_is_never_too_narrow_to_read_nor_wider_than_it_needs() -> None:
    assert place(500, readable=820)[1] == LEAST
    assert place(4000, readable=820)[1] == MOST
