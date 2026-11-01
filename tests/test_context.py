"""What fills a Conversation's context window (#169), estimated: the Engine
reports how much is used, not by what."""

from __future__ import annotations

from osiris.harness.context import Slice, slices


def test_what_is_used_is_shared_by_size_and_the_rest_is_free() -> None:
    sizes = {"instructions": 4000, "questions": 1000, "answers": 2000, "tools": 3000}
    assert slices(sizes, used=10_000, window=40_000) == [
        Slice("instructions", 4000),
        Slice("questions", 1000),
        Slice("answers", 2000),
        Slice("tools", 3000),
        Slice("free", 30_000),
    ]


def test_what_the_messages_do_not_account_for_is_the_engines_instructions() -> None:
    """Its own prompt and the tool catalogue are sent but not listed."""
    sizes = {"instructions": 0, "questions": 100, "answers": 100, "tools": 0}
    assert slices(sizes, used=1000, window=2000) == [
        Slice("instructions", 800),
        Slice("questions", 100),
        Slice("answers", 100),
        Slice("tools", 0),
        Slice("free", 1000),
    ]
