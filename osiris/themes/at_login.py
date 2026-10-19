"""What a home needs at login, decided from what it last had.

A home records the Osiris version it was last brought up to. Re-applying the
person's own Theme regenerates everything Osiris keeps in it, so after an
upgrade that is done once, at the next login (CONTEXT.md).
"""

from __future__ import annotations


def theme_to_apply(
    chosen: str | None, brought_up_to: str | None, version: str, default: str
) -> str | None:
    """The Theme to apply now, or None when the home needs nothing."""
    if chosen is None:
        return default
    return chosen if brought_up_to != version else None
