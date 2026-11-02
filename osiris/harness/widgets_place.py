"""Where the Conversation's widgets go (#169), by the room there is. They never
cover the messages: in the margin the centred messages leave, else in a
column the messages move over for, else in a dropdown from their button."""

from __future__ import annotations

#: Room either side of a card.
GAP = 14
#: The narrowest the messages may be made to make room for a column.
NARROWEST = 420


def place(width: float, readable: float, card: float) -> str:
    """Where they go in a Conversation ``width`` wide, whose messages are at
    most ``readable`` wide and centred: "float", "beside" or "dropdown"."""
    room = card + 2 * GAP
    if (width - min(width, readable)) / 2 >= room:
        return "float"
    if width - room >= NARROWEST:
        return "beside"
    return "dropdown"
