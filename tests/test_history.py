"""Past Conversations as the sidebar shows them: grouped by Project, the most
recent first, with those that have no Project after."""

from __future__ import annotations

from pathlib import Path

from osiris.harness.engine import Past
from osiris.harness.history import Project, group

HOME = Path("/home/tester")
POMODORO = HOME / "Code" / "pomodoro"
OSIRIS = HOME / "Code" / "osiris"


def past(session: str, folder: Path, updated: float) -> Past:
    return Past(session, session.title(), folder, updated)


def test_conversations_in_a_projects_folder_are_grouped_under_it() -> None:
    timer = past("timer", POMODORO, 30)
    pause = past("pause", POMODORO, 20)
    theme = past("theme", HOME, 25)
    projects, loose = group([timer, theme, pause], HOME)
    assert projects == [Project("pomodoro", POMODORO, [timer, pause])]
    assert loose == [theme]


def test_the_project_worked_in_most_recently_comes_first() -> None:
    old = past("old", OSIRIS, 10)
    new = past("new", POMODORO, 40)
    projects, _ = group([new, old], HOME)
    assert [p.name for p in projects] == ["pomodoro", "osiris"]
