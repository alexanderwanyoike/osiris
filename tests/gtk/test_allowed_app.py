"""The App takes back a saved rule (#181): from the Engine, and into the log."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from osiris.harness.log import LOG_FILE
from osiris.harness.saved_rules import SavedRule
from tests.test_harness import HOME

from .test_side_by_side import app

NPM = SavedRule("rule_1", "bash", "npm *", Path("/home/tester/Code/timer"))


def test_taking_back_a_rule_removes_it_at_the_engine_and_logs_it() -> None:
    stand_in, _engine = app()
    removed: list[str] = []
    stand_in.saved = SimpleNamespace(
        saved_rules=lambda: [NPM], remove_saved_rule=removed.append
    )
    assert stand_in.read_saved_rules() == [NPM]
    stand_in.remove_saved_rule(NPM)
    assert removed == ["rule_1"]
    logged = [
        json.loads(line)
        for line in stand_in.log._files.read(HOME / LOG_FILE).splitlines()
    ]
    assert {
        "kind": "rule-removed",
        "action": "bash",
        "resource": "npm *",
        "project": "/home/tester/Code/timer",
    }.items() <= logged[-1].items()
