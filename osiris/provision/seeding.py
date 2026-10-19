"""Files a person keeps in their home, which Osiris writes only once.

Setup runs again on every upgrade and the engine on every Theme switch, so
anything either writes into a home must not undo what the person changed
there (CONTEXT.md).
"""

from __future__ import annotations


def may_write(existing: str | None) -> bool:
    """Whether Osiris may write a file the person keeps, given what is there."""
    return existing is None
