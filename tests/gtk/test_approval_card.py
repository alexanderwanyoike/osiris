"""The card an action outside the tier waits on: what it is, exactly, and the
person's answer."""

from __future__ import annotations

from approval_card import ApprovalCard
from gi.repository import Gtk

from osiris.harness.activity import Step
from osiris.harness.harness import Answer

from .conftest import texts, widgets

HELD = Step("shell", ("ls /etc",), call="call_1", input={"command": "ls -la /etc"})


def card() -> tuple[ApprovalCard, list[tuple[Answer, str]]]:
    answers: list[tuple[Answer, str]] = []
    return ApprovalCard(
        HELD, on_answer=lambda answer, reply: answers.append((answer, reply))
    ), answers


def button(widget: Gtk.Widget, label: str) -> Gtk.Button:
    return next(
        w
        for w in widgets(widget)
        if isinstance(w, Gtk.Button) and w.get_label() == label
    )


def test_the_card_names_the_action_and_its_exact_input() -> None:
    widget, _ = card()
    assert "Run a command?" in texts(widget)
    assert "ls -la /etc" in texts(widget)


def test_each_button_gives_its_answer() -> None:
    widget, answers = card()
    for label in ("Allow once", "Allow for this Conversation", "Deny"):
        button(widget, label).emit("clicked")
    assert answers == [
        (Answer.ONCE, ""),
        (Answer.CONVERSATION, ""),
        (Answer.DENY, ""),
    ]


def test_a_typed_reply_is_sent_in_the_actions_place() -> None:
    widget, answers = card()
    entry = next(w for w in widgets(widget) if isinstance(w, Gtk.Entry))
    entry.set_text("Look in /etc/osiris only")
    entry.emit("activate")
    assert answers == [(Answer.DENY, "Look in /etc/osiris only")]
