"""The Harness's side of an admin password request: a card in the Conversation
whose command asks, answered once, by the person or by lapsing (ADR 0018)."""

from __future__ import annotations

from types import SimpleNamespace

import main
from gi.repository import GLib, Gtk

from osiris.harness import admin
from osiris.harness.admin import request_of
from osiris.harness.conversation import Conversation
from osiris.platform.processes import FakeProcesses, Process

from .conftest import find

ME = 1000
SUDO_LINE = ("/usr/bin/sudo", "-k", "-A", "pacman", "-S", "cowsay")
COMMAND = ["pacman", "-S", "cowsay"]


def process(
    pid: int,
    parent: int,
    name: str,
    *cmdline: str,
    euid: int = ME,
    exe: str | None = None,
) -> Process:
    return Process(pid, parent, name, ME, euid, tuple(cmdline), exe)


PROCESSES = FakeProcesses({
    50: process(50, 1, "opencode", "/usr/bin/opencode", "serve", "--service",
                exe="/usr/bin/opencode"),
    100: process(100, 50, "bash", "/usr/bin/bash", "-c", "sudo pacman -S cowsay",
                 exe="/usr/bin/bash"),
    200: process(200, 100, "sudo", *SUDO_LINE, euid=0),
    300: process(300, 200, "askpass", *admin.HELPER_ARGV, "[sudo] password: ",
                 exe="/usr/bin/python3.14"),
    400: process(400, 100, "steal", "/home/tester/steal", exe="/home/tester/steal"),
})  # fmt: skip


class Invocation:
    def __init__(self) -> None:
        self.values: list[tuple[bool, str]] = []
        self.errors: list[str] = []

    def return_value(self, value: GLib.Variant) -> None:
        self.values.append(value.unpack())

    def return_dbus_error(self, name: str, _message: str) -> None:
        self.errors.append(name)


class Harness:
    def __init__(self, sudo_session: str | None) -> None:
        self.sudo_session = sudo_session
        self.answers: list[tuple[str, tuple[str, ...], bool]] = []

    def running_sudo(self) -> str | None:
        return self.sudo_session

    def admin_answered(
        self, session: str, request: admin.Request, *, approved: bool
    ) -> None:
        self.answers.append((session, request.command, approved))


def app(sudo_session: str | None = "ses_1", engine: int | None = 50) -> SimpleNamespace:
    talk = Conversation()
    talk.asked("install cowsay")
    state = SimpleNamespace(
        processes=PROCESSES, uid=ME, engine_pid=engine,
        harness=Harness(sudo_session), session="ses_1", conversation=talk,
        backgrounded={}, admin_pending={}, open=True, log=None,
        drawer=SimpleNamespace(refresh=lambda **_kw: None, summon=lambda: None),
    )  # fmt: skip
    for name in ("_conversation_of", "admin_answer", "admin_card", "_show_admin_card"):
        method = getattr(main.Application, name)
        setattr(state, name, lambda *args, _m=method, **kw: _m(state, *args, **kw))
    state.load_history = lambda: None
    return state


def test_the_agents_sudo_shows_a_card_in_its_conversation() -> None:
    state, call = app(), Invocation()
    main.Application.admin_asked(state, 300, COMMAND, call)
    assert state.conversation.turns[-1].admin == request_of(SUDO_LINE)
    assert (call.values, call.errors) == ([], [])


def test_allow_hands_the_password_to_the_helper_once_and_clears_the_card() -> None:
    state, call = app(), Invocation()
    main.Application.admin_asked(state, 300, COMMAND, call)
    card = state.admin_card(state.conversation.turns[-1].admin)
    find(card, Gtk.PasswordEntry).set_text("hunter2")
    find(card, Gtk.Button, "Allow").emit("clicked")
    find(card, Gtk.Button, "Deny").emit("clicked")
    assert call.values == [(True, "hunter2")]
    assert state.conversation.turns[-1].admin is None
    assert state.harness.answers == [("ses_1", tuple(COMMAND), True)]
    assert state.admin_pending == {}


def test_deny_refuses_the_helper() -> None:
    state, call = app(), Invocation()
    main.Application.admin_asked(state, 300, COMMAND, call)
    card = state.admin_card(state.conversation.turns[-1].admin)
    find(card, Gtk.Button, "Deny").emit("clicked")
    assert call.values == [(False, "")]
    assert state.harness.answers == [("ses_1", tuple(COMMAND), False)]


def test_a_card_that_lapses_refuses_and_goes_away() -> None:
    state, call = app(), Invocation()
    main.Application.admin_asked(state, 300, COMMAND, call)
    main.Application.admin_answer(state, "ses_1", None)
    assert call.values == [(False, "")]
    assert state.conversation.turns[-1].admin is None


def test_attack_a_caller_that_is_not_the_helper_is_refused_with_no_card() -> None:
    state, call = app(), Invocation()
    main.Application.admin_asked(state, 400, COMMAND, call)
    assert call.errors == [admin.REFUSED]
    assert state.conversation.turns[-1].admin is None


def test_a_sudo_that_is_not_the_agents_is_left_to_the_helper() -> None:
    state, call = app(engine=999), Invocation()
    main.Application.admin_asked(state, 300, COMMAND, call)
    assert call.errors == [admin.NOT_THE_AGENTS]
    assert state.conversation.turns[-1].admin is None


def test_a_second_request_while_one_waits_is_refused() -> None:
    state, first, second = app(), Invocation(), Invocation()
    main.Application.admin_asked(state, 300, COMMAND, first)
    main.Application.admin_asked(state, 300, COMMAND, second)
    assert second.values == [(False, "")]
    assert first.values == []


def test_an_answer_that_ends_lets_its_card_lapse() -> None:
    state, call = app(), Invocation()
    main.Application.admin_asked(state, 300, COMMAND, call)
    main.Application._ended(state, "ses_1", Conversation())
    assert call.values == [(False, "")]


def test_attack_a_debugger_attached_while_the_card_waits_gets_no_password() -> None:
    """Checked again when the person allows: the helper waits for minutes, and
    the agent's shell, its ancestor, may attach to it meanwhile."""
    state, call = app(), Invocation()
    state.processes = FakeProcesses(dict(PROCESSES.table))
    main.Application.admin_asked(state, 300, COMMAND, call)
    helper = state.processes.table[300]
    state.processes.table[300] = Process(
        helper.pid, helper.parent, helper.name, helper.uid, helper.euid,
        helper.cmdline, helper.exe, tracer=100,
    )  # fmt: skip
    card = state.admin_card(state.conversation.turns[-1].admin)
    find(card, Gtk.PasswordEntry).set_text("hunter2")
    find(card, Gtk.Button, "Allow").emit("clicked")
    assert call.values == [(False, "")]
