"""The Engine's task list for an answer: the steps it plans, as it reports
them (#162). opencode 2.2.4 sends the whole list with each todowrite call."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

#: The Engine's tool that reports the list.
TASK_TOOL = "todowrite"


class Progress(Enum):
    TO_DO = "to do"
    UNDER_WAY = "under way"
    DONE = "done"
    DROPPED = "dropped"


#: opencode's statuses, in its own words.
_PROGRESS = {
    "pending": Progress.TO_DO,
    "in_progress": Progress.UNDER_WAY,
    "completed": Progress.DONE,
    "cancelled": Progress.DROPPED,
}


@dataclass(frozen=True)
class Task:
    text: str
    progress: Progress


def tasks_of(arguments: Mapping[str, object]) -> list[Task]:
    """The list a todowrite call carries; anything it does not say is to do."""
    items = arguments.get("todos")
    if not isinstance(items, list):
        return []
    return [
        Task(
            str(item.get("content", "")),
            _PROGRESS.get(str(item.get("status")), Progress.TO_DO),
        )
        for item in items
        if isinstance(item, dict)
    ]
