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


def test_the_grid_gives_each_kind_its_share_of_squares() -> None:
    from osiris.harness.context import grid

    shared = [
        Slice("instructions", 30),
        Slice("questions", 5),
        Slice("answers", 15),
        Slice("tools", 0),
        Slice("free", 50),
    ]
    squares = grid(shared, 20)
    assert len(squares) == 20
    assert (
        squares
        == ["instructions"] * 6 + ["questions"] + ["answers"] * 3 + ["free"] * 10
    )


def test_a_kind_with_any_tokens_gets_at_least_one_square() -> None:
    from osiris.harness.context import grid

    shared = [Slice("instructions", 1), Slice("free", 999)]
    assert grid(shared, 10).count("instructions") == 1
