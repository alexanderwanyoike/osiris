"""What a question changed, from the commits it made to Programs: each file a
commit touched, with its lines added and removed and its own diff."""

from __future__ import annotations

from osiris.harness.engine import FileChange

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
