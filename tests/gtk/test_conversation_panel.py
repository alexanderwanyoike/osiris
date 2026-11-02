"""The Conversation panel (#169): where it runs, its connectors, its context
and its changes."""

from __future__ import annotations

from .conftest import texts


def panel():
    from conversation_panel import ConversationPanel

    return ConversationPanel()


def test_it_says_where_the_conversation_runs() -> None:
    shown = panel()
    shown.show_where("timer", "main", "GPT-6.1 Terra")
    words = texts(shown)
    assert "timer" in words and "main" in words and "GPT-6.1 Terra" in words


def test_a_folder_that_is_no_repository_shows_no_branch() -> None:
    shown = panel()
    shown.show_where("Home", "", "GPT-6.1 Terra")
    assert not shown.branch.get_visible()


def test_each_connector_shows_with_its_state() -> None:
    from osiris.harness.connectors import State

    shown = panel()
    shown.show_connectors(
        {"wiki": State("connected"), "tracker": State("needs_auth", "", "mcp_x")}
    )
    words = texts(shown)
    assert "wiki" in words and "Connected" in words
    assert "tracker" in words and "Needs signing in" in words


def test_with_no_connectors_it_says_where_to_add_one() -> None:
    shown = panel()
    shown.show_connectors({})
    assert any("Settings" in text for text in texts(shown))


def test_context_is_a_grid_of_squares_with_a_legend_marked_approximate() -> None:
    from conversation_panel import SQUARES

    from osiris.harness.context import Slice

    from .conftest import widgets

    shown = panel()
    shown.show_context(
        [
            Slice("instructions", 6000),
            Slice("questions", 1000),
            Slice("answers", 2000),
            Slice("tools", 1000),
            Slice("free", 90_000),
        ],
        used=10_000,
        window=100_000,
    )
    squares = [w for w in widgets(shown) if w.has_css_class("harness-context-square")]
    assert len(squares) == SQUARES
    assert sum(s.has_css_class("instructions") for s in squares) == SQUARES * 6 // 100
    words = texts(shown)
    assert "10,000 of 100,000 tokens" in words
    assert "Instructions" in words and "6%" in words
    assert any("pproximate" in text for text in words)


def test_each_question_that_changed_something_opens_its_changes() -> None:
    from gi.repository import Gtk

    from .conftest import widgets

    opened: list[int] = []
    shown = panel()
    shown.show_changes(
        [(1, "make it calm", 2), (3, "tidy the timer", 1)], opened.append
    )
    words = texts(shown)
    assert "make it calm" in words and "2 changes" in words
    assert "tidy the timer" in words and "1 change" in words
    rows = [w for w in widgets(shown) if isinstance(w, Gtk.ListBoxRow)]
    rows[1].emit("activate")
    assert opened == [3]


def test_with_nothing_changed_it_says_so() -> None:
    shown = panel()
    shown.show_changes([], lambda _i: None)
    assert "Nothing changed yet." in texts(shown)


def test_a_kind_present_but_under_one_percent_says_so_rather_than_none() -> None:
    from osiris.harness.context import Slice

    shown = panel()
    shown.show_context(
        [Slice("questions", 30), Slice("free", 99_970)], used=30, window=100_000
    )
    assert "<1%" in texts(shown)
