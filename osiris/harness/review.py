"""A comment on lines of a change, as it reaches Thoth (#157).

The person picks lines of a unified diff; the model needs them as lines of
the file as it is now.
"""

from __future__ import annotations

import re

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _numbered(patch: str) -> list[int | None]:
    """Each line of the patch as a line of the new file: a removed line is
    where it was taken out; a header has none."""
    numbers: list[int | None] = []
    new: int | None = None
    for line in patch.split("\n"):
        hunk = _HUNK.match(line)
        if hunk:
            new = int(hunk.group(1))
            numbers.append(None)
        elif new is not None and line[:1] in (" ", "+"):
            numbers.append(new)
            new += 1
        elif new is not None and line[:1] == "-":
            numbers.append(new)
        else:
            numbers.append(None)
    return numbers


def file_lines(patch: str, first: int, last: int) -> tuple[int, int] | None:
    """The file's lines for the patch's lines ``first`` to ``last``, counted
    from 1; None when none of them is in the file."""
    picked = [n for n in _numbered(patch)[first - 1 : last] if n is not None]
    return (min(picked), max(picked)) if picked else None


def comment(path: str, lines: tuple[int, int], text: str) -> str:
    start, end = lines
    where = f"line {start}" if start == end else f"lines {start} to {end}"
    return f"About {path}, {where}:\n\n{text}"
