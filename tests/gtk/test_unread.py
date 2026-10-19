"""Conversations as chats: an answer the person has not seen is unread, and
the desktop tells them Osiris got back to them."""

from __future__ import annotations

from osiris.harness.engine import Finished, Text

from .test_side_by_side import App, app, asked, heard


def test_an_answer_ending_off_screen_leaves_its_conversation_unread() -> None:
    stand_in, _ = app()
    asked(stand_in, "make it calm")
    stand_in.new_conversation()
    heard(stand_in, Text("ses_1", "Calmer now."))
    heard(stand_in, Finished("ses_1"))
    assert stand_in.unread.sessions() == frozenset({"ses_1"})


def test_an_answer_ending_on_screen_with_the_drawer_put_away_is_unread() -> None:
    stand_in, _ = app()
    asked(stand_in, "make it calm")
    stand_in.open = False
    heard(stand_in, Finished("ses_1"))
    assert stand_in.unread.sessions() == frozenset({"ses_1"})


def test_an_answer_the_person_watched_end_in_the_open_drawer_is_read() -> None:
    stand_in, _ = app()
    asked(stand_in, "make it calm")
    heard(stand_in, Finished("ses_1"))
    assert stand_in.unread.sessions() == frozenset()


def test_an_answer_ending_unread_is_told_on_the_desktop_by_its_conversation() -> None:
    """Notified under its session, so a newer answer replaces the older
    notification rather than piling up."""
    stand_in, _ = app()
    asked(stand_in, "make it calm")
    stand_in.open = False
    heard(stand_in, Finished("ses_1"))
    assert [session for session, _ in stand_in.sent] == ["ses_1"]


def test_an_answer_the_person_watched_end_is_not_told_on_the_desktop() -> None:
    stand_in, _ = app()
    asked(stand_in, "make it calm")
    heard(stand_in, Finished("ses_1"))
    assert stand_in.sent == []


def test_the_sidebar_is_told_which_conversations_are_unread() -> None:
    """The drawer hands the sidebar the Application's unread_sessions."""
    stand_in, _ = app()
    asked(stand_in, "make it calm")
    stand_in.new_conversation()
    heard(stand_in, Finished("ses_1"))
    assert stand_in.unread_sessions == frozenset({"ses_1"})


def answered_off_screen() -> App:
    """Osiris finished "make it calm" (ses_1) while ses_2 was on screen."""
    stand_in, _ = app()
    asked(stand_in, "make it calm")
    stand_in.new_conversation()
    asked(stand_in, "something else")
    heard(stand_in, Finished("ses_1"))
    return stand_in


def test_opening_an_unread_conversation_marks_it_read() -> None:
    stand_in = answered_off_screen()
    stand_in.open_past("ses_1")
    assert stand_in.unread.sessions() == frozenset()


def test_opening_an_unread_conversation_takes_its_notification_away() -> None:
    """The desktop should not go on telling them about what they now see."""
    stand_in = answered_off_screen()
    stand_in.open_past("ses_1")
    assert stand_in.withdrawn == ["ses_1"]


def test_bringing_the_drawer_back_to_an_unread_conversation_marks_it_read() -> None:
    """It was answered on screen while the drawer was put away; opening the
    drawer puts it in front of the person."""
    stand_in, _ = app()
    asked(stand_in, "make it calm")
    stand_in.open = False
    heard(stand_in, Finished("ses_1"))
    stand_in.toggle()
    assert stand_in.unread.sessions() == frozenset()
    assert stand_in.withdrawn == ["ses_1"]
