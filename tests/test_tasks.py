"""The Engine's task list as Thoth reads it from a todowrite call."""

from __future__ import annotations

from osiris.harness.tasks import Progress, Task, tasks_of


def test_every_status_the_engine_uses_has_a_progress() -> None:
    given = {
        "todos": [
            {"content": "a", "status": "pending"},
            {"content": "b", "status": "in_progress"},
            {"content": "c", "status": "completed"},
            {"content": "d", "status": "cancelled"},
        ]
    }
    assert [task.progress for task in tasks_of(given)] == [
        Progress.TO_DO,
        Progress.UNDER_WAY,
        Progress.DONE,
        Progress.DROPPED,
    ]


def test_a_list_it_cannot_read_is_no_list() -> None:
    assert tasks_of({}) == []
    assert tasks_of({"todos": "make two files"}) == []
    assert tasks_of({"todos": ["make two files"]}) == []


def test_a_status_it_does_not_know_is_to_do() -> None:
    assert tasks_of({"todos": [{"content": "a", "status": "blocked"}]}) == [
        Task("a", Progress.TO_DO)
    ]
