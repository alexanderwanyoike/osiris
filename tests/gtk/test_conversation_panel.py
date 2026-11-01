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
