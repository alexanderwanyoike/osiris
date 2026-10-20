"""The admin password card: the exact command sudo will run, a password entry,
Allow and Deny (ADR 0018)."""

from __future__ import annotations

from admin_card import AdminCard
from gi.repository import Gtk

from osiris.harness.admin import Request, request_of

from .conftest import find, texts, widgets


class Answers:
    def __init__(self) -> None:
        self.allowed: list[str] = []
        self.denied = 0

    def deny(self) -> None:
        self.denied += 1


def card(request: Request) -> tuple[AdminCard, Answers]:
    answers = Answers()
    widget = AdminCard(request, on_allow=answers.allowed.append, on_deny=answers.deny)
    return widget, answers


def entry(root: Gtk.Widget) -> Gtk.PasswordEntry:
    found = find(root, Gtk.PasswordEntry)
    assert isinstance(found, Gtk.PasswordEntry)
    return found


def test_the_card_shows_the_exact_command_in_monospace() -> None:
    widget, _ = card(request_of(("sudo", "-k", "-A", "pacman", "-S", "cowsay")))
    assert "Osiris needs your password to run:" in texts(widget)
    command = next(
        w
        for w in widgets(widget)
        if isinstance(w, Gtk.Label) and w.get_text() == "pacman -S cowsay"
    )
    assert command.has_css_class("monospace")


def test_a_shell_string_is_labelled_as_one() -> None:
    widget, _ = card(request_of(("sudo", "-A", "sh", "-c", "rm -rf /var/cache/x")))
    assert "sh -c 'rm -rf /var/cache/x'" in texts(widget)
    assert "A shell command, shown in full: all of it runs as root." in texts(widget)


def test_a_script_says_its_contents_are_not_shown() -> None:
    widget, _ = card(request_of(("sudo", "-A", "./install.sh")))
    assert "Runs a script; its contents are not shown." in texts(widget)


def test_another_target_user_is_named() -> None:
    widget, _ = card(request_of(("sudo", "-A", "-u", "http", "id")))
    assert "Osiris needs your password to run as http:" in texts(widget)


def test_allow_hands_over_the_password_and_clears_the_entry() -> None:
    widget, answers = card(request_of(("sudo", "-A", "true")))
    entry(widget).set_text("hunter2")
    find(widget, Gtk.Button, "Allow").emit("clicked")
    assert answers.allowed == ["hunter2"]
    assert entry(widget).get_text() == ""


def test_enter_in_the_entry_allows() -> None:
    widget, answers = card(request_of(("sudo", "-A", "true")))
    entry(widget).set_text("hunter2")
    entry(widget).emit("activate")
    assert answers.allowed == ["hunter2"]


def test_allow_with_no_password_does_nothing() -> None:
    widget, answers = card(request_of(("sudo", "-A", "true")))
    find(widget, Gtk.Button, "Allow").emit("clicked")
    assert answers.allowed == []


def test_deny_refuses() -> None:
    widget, answers = card(request_of(("sudo", "-A", "true")))
    entry(widget).set_text("hunter2")
    find(widget, Gtk.Button, "Deny").emit("clicked")
    assert answers.denied == 1
    assert answers.allowed == []
    assert entry(widget).get_text() == ""
