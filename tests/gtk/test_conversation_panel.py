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
