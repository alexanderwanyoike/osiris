"""Each Conversation's status at a glance in the sidebar (#152): whether it is
working, waiting for the person, or done and not yet read."""

from __future__ import annotations

from collections.abc import Collection
from enum import Enum


class Status(Enum):
    WORKING = "Working"
    WAITING = "Waiting for you"
    DONE = "Done"


def status_of(
    session: str,
    *,
    running: Collection[str],
    waiting: Collection[str],
    unread: Collection[str],
) -> Status | None:
    """Waiting comes first: an answer held for the person is still running."""
    if session in waiting:
        return Status.WAITING
    if session in running:
        return Status.WORKING
    if session in unread:
        return Status.DONE
    return None
