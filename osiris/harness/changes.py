"""What a question changed, from the commits it made to Programs. Each commit
is recorded with the question in the Harness log, so this works for any
Program from any Conversation, reopened or not."""

from __future__ import annotations

import re

from osiris.harness.engine import FileChange

_FILE = re.compile(r"^diff --git a/(.+) b/(.+)$", re.MULTILINE)


def file_changes(program: str, patch: str) -> tuple[FileChange, ...]:
    """Each file in a commit's patch, named under its Program."""
    starts = [found.start() for found in _FILE.finditer(patch)]
    ends = [*starts[1:], len(patch)] if starts else []
    sections = [
        patch[start:end].rstrip("\n") for start, end in zip(starts, ends, strict=True)
    ]
    return tuple(_change(program, section) for section in sections)


def _change(program: str, section: str) -> FileChange:
    lines = section.split("\n")
    path = _FILE.match(lines[0])
    assert path is not None
    if any(line.startswith("new file mode") for line in lines[:4]):
        status = "added"
    elif any(line.startswith("deleted file mode") for line in lines[:4]):
        status = "deleted"
    else:
        status = "modified"
    body = lines[next(i for i, line in enumerate(lines) if line.startswith("@@")) :]
    return FileChange(
        f"{program}/{path.group(2)}",
        status,
        sum(1 for line in body if line.startswith("+")),
        sum(1 for line in body if line.startswith("-")),
        section,
    )
