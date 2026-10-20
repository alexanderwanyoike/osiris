"""The helper's own dialog, for a sudo that is not the agent's (ADR 0018)."""

from __future__ import annotations

from askpass import AdminDialog
from gi.repository import Gtk

from osiris.harness.admin import request_of

from .conftest import find, texts

PACMAN = request_of(("sudo", "-A", "pacman", "-S", "cowsay"))


def dialog() -> tuple[AdminDialog, list[str | None]]:
    answers: list[str | None] = []
    return AdminDialog(PACMAN, asker="claude", on_answer=answers.append), answers


def test_the_dialog_names_the_program_asking_and_the_command() -> None:
    window, _ = dialog()
    assert "claude needs your password to run:" in texts(window)
    assert "pacman -S cowsay" in texts(window)


def test_allow_answers_with_the_password() -> None:
    window, answers = dialog()
    find(window, Gtk.PasswordEntry).set_text("hunter2")
    find(window, Gtk.Button, "Allow").emit("clicked")
    assert answers == ["hunter2"]


def test_deny_answers_with_nothing() -> None:
    window, answers = dialog()
    find(window, Gtk.Button, "Deny").emit("clicked")
    assert answers == [None]


def test_closing_the_dialog_denies() -> None:
    window, answers = dialog()
    window.emit("close-request")
    assert answers == [None]


def test_the_dialog_answers_once() -> None:
    window, answers = dialog()
    find(window, Gtk.PasswordEntry).set_text("hunter2")
    find(window, Gtk.Button, "Allow").emit("clicked")
    window.emit("close-request")
    assert answers == ["hunter2"]
