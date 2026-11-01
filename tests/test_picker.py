"""The composer's picker (#153): / or @ at the start of a word opens it, and
what follows filters it."""

from __future__ import annotations

from pathlib import Path

import pytest

from osiris.harness.picker import Entry, Reference, Trigger, references, trigger


@pytest.mark.parametrize(
    ("typed", "found"),
    [
        ("fix @REA", Trigger("@", 4, "REA")),
        ("/rev", Trigger("/", 0, "rev")),
        ("@", Trigger("@", 0, "")),
        ("look at\n/", Trigger("/", 8, "")),
        ("a/b", None),
        ("mail me@home", None),
        ("@main.py done", None),
        ("", None),
    ],
)
def test_a_sign_at_the_start_of_the_word_being_typed_opens_the_picker(
    typed: str, found: Trigger | None
) -> None:
    assert trigger(typed, len(typed)) == found


def test_what_is_typed_filters_starts_first_then_contains_ignoring_case() -> None:
    from osiris.harness.picker import Entry, matching

    readme = Entry("file", "README.md", "README.md", "")
    main = Entry("file", "src/main.py", "main.py", "src")
    domain = Entry("file", "src/domain.py", "domain.py", "src")
    assert matching([readme, domain, main], "ma") == [main, domain]
    assert matching([readme, domain, main], "READ") == [readme]
    assert matching([readme, domain, main], "") == [readme, domain, main]


def test_a_programs_files_are_offered_by_where_they_are_in_it() -> None:
    from osiris.harness.picker import Entry, project_files

    source = Path("/home/tester/Code/timer")
    offered = project_files(source, [Path("README.md"), Path("timer/clock.py")])
    assert offered == [
        Entry("file", "/home/tester/Code/timer/README.md", "README.md", ""),
        Entry("file", "/home/tester/Code/timer/timer/clock.py", "timer/clock.py", ""),
    ]


README = Entry("file", "/home/tester/Code/timer/README.md", "README.md", "")
REVIEW = Entry("skill", "review", "review", "")


@pytest.mark.parametrize(
    ("text", "found"),
    [
        ("/review @README.md", ((REVIEW, 0, 7), (README, 8, 18))),
        ("see @README.md.", ((README, 4, 14),)),
        ("@README.md then @README.md", ((README, 0, 10),)),
        ("mail@README.md /reviewer", ()),
        ("the token was deleted", ()),
    ],
)
def test_what_was_picked_is_found_where_it_still_stands_in_the_text(
    text: str, found: tuple[tuple[Entry, int, int], ...]
) -> None:
    assert references(text, [README, REVIEW]) == tuple(
        Reference(entry, start, end) for entry, start, end in found
    )
