"""Where the Conversation's widgets go (#169), by the room there is: never
over the messages."""

from __future__ import annotations

import pytest

from osiris.harness.widgets_place import place


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
    assert place(width, readable=760, card=260) == where
