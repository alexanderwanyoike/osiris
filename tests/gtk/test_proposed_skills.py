"""Skills Osiris proposes (#154), as the App handles them: on the answer that
proposed them, written only when the person keeps one."""

from __future__ import annotations

from osiris.harness.engine import Finished
from osiris.harness.proposals import Proposal, skill_path
from osiris.platform import FakeFileSystem
from tests.test_harness import HOME

from .test_side_by_side import app, asked, heard

TIDY = Proposal("tidy-imports", "Sort imports", "Run ruff.")


def proposed(stand_in) -> None:
    stand_in.log.write(
        "proposed-skill",
        name=TIDY.name,
        description=TIDY.description,
        body=TIDY.body,
    )


def test_an_answer_that_proposed_a_skill_carries_the_proposal() -> None:
    stand_in, _engine = app()
    conversation = asked(stand_in, "tidy my imports")
    proposed(stand_in)
    heard(stand_in, Finished(stand_in.harness.session or ""))
    assert conversation.turns[-1].proposals == [TIDY]


def test_a_kept_proposal_is_written_as_a_skill_and_the_choice_logged() -> None:
    stand_in, _engine = app()
    stand_in.files = files = FakeFileSystem()
    stand_in.keep_skill(TIDY)
    assert files.exists(skill_path(HOME, TIDY))
    assert stand_in.log.decided() == {"tidy-imports": True}


def test_a_declined_proposal_writes_nothing_and_the_choice_is_logged() -> None:
    stand_in, _engine = app()
    stand_in.files = files = FakeFileSystem()
    stand_in.decline_skill(TIDY)
    assert not files.exists(skill_path(HOME, TIDY))
    assert stand_in.log.decided() == {"tidy-imports": False}
