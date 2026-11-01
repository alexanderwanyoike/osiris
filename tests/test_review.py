"""A comment on lines of a change, as it reaches Thoth (#157)."""

from __future__ import annotations

import pytest

from osiris.harness.review import comment, file_lines

PATCH = (
    "Index: main.py\n"
    "@@ -10,3 +10,4 @@\n"
    " def tick():\n"
    "-    return 1\n"
    "+    left -= 1\n"
    "+    return left\n"
    " \n"
)


@pytest.mark.parametrize(
    ("first", "last", "lines"),
    [
        (3, 3, (10, 10)),  # an unchanged line keeps its number
        (5, 6, (11, 12)),  # the added lines
        (4, 4, (11, 11)),  # a removed line is where it was taken out
        (1, 7, (10, 13)),  # the whole patch, headers ignored
    ],
)
def test_lines_picked_in_a_diff_are_lines_of_the_file_as_it_is_now(
    first: int, last: int, lines: tuple[int, int]
) -> None:
    assert file_lines(PATCH, first, last) == lines


def test_lines_with_no_place_in_the_file_name_none() -> None:
    assert file_lines(PATCH, 1, 2) is None


def test_a_comment_names_its_file_and_lines() -> None:
    assert comment("main.py", (11, 12), "Count down from five instead.") == (
        "About main.py, lines 11 to 12:\n\nCount down from five instead."
    )
    assert comment("main.py", (11, 11), "Why?").startswith("About main.py, line 11:")
