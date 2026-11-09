"""What a question changed, from the commits it made to Programs: each file a
commit touched, with its lines added and removed and its own diff."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from osiris.harness.changes import credit_shell_commits
from osiris.harness.engine import FileChange
from osiris.harness.log import Change, HarnessLog
from osiris.platform import FakeFileSystem

ASKED = datetime(2026, 11, 9, 10, 0, tzinfo=UTC)


class History:
    """A Program's commits since a time, as Programs reads them from git."""

    def __init__(self, found: dict[str, list[tuple[str, str]]]) -> None:
        self.found = found
        self.since: list[tuple[str, datetime]] = []

    def commits_since(self, name: str, since: datetime) -> list[tuple[str, str]]:
        self.since.append((name, since))
        return self.found.get(name, [])

    def label(self, name: str) -> str:
        return name.replace("-", " ").title()


def asked_log() -> HarnessLog:
    log = HarnessLog(FakeFileSystem(), Path("/home/tester/log.jsonl"), lambda: ASKED)
    log.write("sent", session="ses_1", text="build me a habit tracker")
    log.write(
        "changed",
        session="ses_1",
        summary="Made Daily Habits",
        undo={"action": "trash_program", "name": "daily-habits"},
        program="daily-habits",
    )
    return log


def test_commits_made_in_a_shell_are_the_questions_changes() -> None:
    """A Program's commits the Osiris tools did not log, made since the
    question was asked, count as its changes, each undone by a revert
    (#219)."""
    log = asked_log()
    history = History({"daily-habits": [("abc123", "Track habits")]})
    credit_shell_commits(log, history, "ses_1")
    assert history.since == [("daily-habits", ASKED)]
    assert log.changes_by_question("ses_1")[-1][-1] == Change(
        "Daily Habits: Track habits",
        {"action": "revert_commit", "name": "daily-habits", "commit": "abc123"},
        "daily-habits",
    )


def test_the_program_a_conversation_runs_in_is_credited_too() -> None:
    """A question asked in a Program's Project may change it with nothing
    but a shell."""
    log = HarnessLog(FakeFileSystem(), Path("/home/tester/log.jsonl"), lambda: ASKED)
    log.write("sent", session="ses_1", text="add a pause button")
    history = History({"pomodoro": [("def456", "Add a pause button")]})
    credit_shell_commits(log, history, "ses_1", project="pomodoro")
    assert [c.summary for c in log.changes_by_question("ses_1")[-1]] == [
        "Pomodoro: Add a pause button"
    ]


def test_a_commit_already_credited_is_not_credited_again() -> None:
    log = asked_log()
    history = History({"daily-habits": [("abc123", "Track habits")]})
    credit_shell_commits(log, history, "ses_1")
    credit_shell_commits(log, history, "ses_1")
    assert len(log.changes_by_question("ses_1")[-1]) == 2


TIDIED = "\n".join(
    (
        "diff --git a/main.py b/main.py",
        "index 1..2 100644",
        "--- a/main.py",
        "+++ b/main.py",
        "@@ -1,2 +1,3 @@",
        " import random",
        "-print(1)",
        "+print(2)",
        "+print(3)",
    )
)
NOTES = "\n".join(
    (
        "diff --git a/notes.md b/notes.md",
        "new file mode 100644",
        "index 0..3",
        "--- /dev/null",
        "+++ b/notes.md",
        "@@ -0,0 +1 @@",
        "+hello",
    )
)
GONE = "\n".join(
    (
        "diff --git a/old.py b/old.py",
        "deleted file mode 100644",
        "index 4..0",
        "--- a/old.py",
        "+++ /dev/null",
        "@@ -1 +0,0 @@",
        "-x = 1",
    )
)


def test_each_file_a_commit_touched_is_a_change_named_under_its_program() -> None:
    from osiris.harness.changes import file_changes

    assert file_changes("coin-flip", "\n".join((TIDIED, NOTES, GONE))) == (
        FileChange("coin-flip/main.py", "modified", 2, 1, TIDIED),
        FileChange("coin-flip/notes.md", "added", 1, 0, NOTES),
        FileChange("coin-flip/old.py", "deleted", 0, 1, GONE),
    )


def test_a_commit_that_changed_nothing_gives_no_changes() -> None:
    from osiris.harness.changes import file_changes

    assert file_changes("coin-flip", "") == ()


def test_a_binary_file_is_a_change_with_no_lines_counted() -> None:
    """git names a changed picture but gives no lines for it."""
    from osiris.harness.changes import file_changes

    icon = "\n".join(
        (
            "diff --git a/icon.png b/icon.png",
            "new file mode 100644",
            "index 0..5",
            "Binary files /dev/null and b/icon.png differ",
        )
    )
    assert file_changes("coin-flip", icon) == (
        FileChange("coin-flip/icon.png", "added", 0, 0, icon),
    )
