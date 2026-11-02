"""Where the Conversation's widgets go (#169), and how wide they are. They
show only with Thoth expanded and the Canvas closed, and never cover the
messages: in the margin the centred messages leave, else in a column the
messages move over for, else not at all. A card is a share of the
Conversation's width, so it suits any window, kept within what reads well."""

from __future__ import annotations

#: A card's share of the Conversation's width.
SHARE = 0.22
#: The narrowest a card reads well at, and the widest it needs.
LEAST = 220
MOST = 300
#: Room either side of a card.
GAP = 14
#: The narrowest the messages may be made to make room for a column.
NARROWEST = 420


def place(
    width: float, readable: float, expanded: bool, canvas: bool
) -> tuple[str, int]:
    """Where the cards go in a Conversation ``width`` wide, whose messages are
    at most ``readable`` wide and centred ("float", "beside" or "hidden"),
    and how wide each card is."""
    card = min(max(round(width * SHARE), LEAST), MOST)
    room = card + 2 * GAP
    if not expanded or canvas:
        return "hidden", card
    if (width - min(width, readable)) / 2 >= room:
        return "float", card
    if width - room >= NARROWEST:
        return "beside", card
    return "hidden", card
