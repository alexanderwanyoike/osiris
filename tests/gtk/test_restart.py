"""The Harness quits onto upgraded code only when nothing is under way, so
D-Bus starts the new code on the next Super+A."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import main

from osiris.harness.conversation import Conversation
from osiris.platform import FakeFileSystem
from osiris.provision.upgrade import Upgrade

MARKER = Path("/usr/share/osiris/setup-ran")


def harness(upgraded: bool, **state: object) -> SimpleNamespace:
    files = FakeFileSystem()
    app = SimpleNamespace(
        open=False,
        conversation=Conversation(),
        backgrounded={},
        program_busy={},
        upgrade=Upgrade(files, MARKER),
        quits=0,
    )
    app.quit = lambda: setattr(app, "quits", app.quits + 1)
    for name, value in state.items():
        setattr(app, name, value)
    if upgraded:
        files.write(MARKER, "0.1.0 2\n")
    return app


def test_an_upgraded_harness_put_away_quits() -> None:
    app = harness(upgraded=True)
    main.Application._restart_if_upgraded(app)
    assert app.quits == 1


def test_an_upgraded_harness_waits_while_the_drawer_is_open() -> None:
    app = harness(upgraded=True, open=True)
    main.Application._restart_if_upgraded(app)
    assert app.quits == 0


def test_an_upgraded_harness_waits_while_an_answer_is_coming() -> None:
    asking = Conversation()
    asking.asked("build me a timer")
    app = harness(upgraded=True, conversation=asking)
    main.Application._restart_if_upgraded(app)
    assert app.quits == 0


def test_an_upgraded_harness_waits_while_a_conversation_off_screen_is_answered() -> (
    None
):
    asking = Conversation()
    asking.asked("build me a timer")
    app = harness(upgraded=True, backgrounded={"ses_1": asking})
    main.Application._restart_if_upgraded(app)
    assert app.quits == 0


def test_an_upgraded_harness_waits_while_a_program_builds() -> None:
    app = harness(upgraded=True, program_busy={"pomodoro": "Installing"})
    main.Application._restart_if_upgraded(app)
    assert app.quits == 0


def test_a_harness_not_upgraded_keeps_running() -> None:
    app = harness(upgraded=False)
    main.Application._restart_if_upgraded(app)
    assert app.quits == 0
