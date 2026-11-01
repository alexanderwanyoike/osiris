"""The composer's picker (#153): / or @ at the start of a word opens it, and
what follows filters it."""

from __future__ import annotations

import pytest

from osiris.harness.picker import Trigger, trigger


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
