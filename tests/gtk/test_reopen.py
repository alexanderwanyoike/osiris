"""A Conversation reopened from history gets back what the log kept: its
tokens, its Program cards and its Undo."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import main

from osiris.harness.engine import ModelRef, PastTurn
from osiris.harness.log import LOG_FILE, HarnessLog
from osiris.platform import FakeFileSystem

GPT = ModelRef("openai", "gpt-5.5")


def test_a_reopened_conversation_offers_its_program_card_and_undo_again() -> None:
    log = HarnessLog(FakeFileSystem(), Path("/home/tester") / LOG_FILE)
    log.write("sent", session="ses_1", text="build me a timer")
    log.write(
        "changed",
        summary="Made Pomodoro",
        undo={"action": "trash_program", "name": "pomodoro"},
        program="pomodoro",
    )
    app = SimpleNamespace(log=log)
    talk = main.Application._restored(
        app, "ses_1", [PastTurn("build me a timer", "Made it.", GPT)]
    )
    assert talk.turns[0].programs == ["pomodoro"]
    assert talk.turns[0].undoable
