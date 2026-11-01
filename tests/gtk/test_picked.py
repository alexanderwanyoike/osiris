"""What the person picks in the message box reaches the Engine with the text,
however the message is sent."""

from __future__ import annotations

import threading

from osiris.harness.picker import Entry, Reference

from .test_side_by_side import app, asked

REVIEW = Reference(Entry("skill", "review", "review", ""), 0, 7)


def sent_off() -> None:
    """Questions go to the Engine on a thread of their own."""
    for thread in threading.enumerate():
        if thread is not threading.current_thread() and thread.daemon:
            thread.join(timeout=5)


def test_what_was_picked_goes_with_a_question() -> None:
    stand_in, engine = app()
    stand_in.ask("/review the timer", (REVIEW,))
    sent_off()
    assert engine.referenced == [("ses_1", (REVIEW,))]


def test_what_was_picked_goes_with_a_message_sent_while_osiris_works() -> None:
    stand_in, engine = app()
    asked(stand_in, "make it calm")
    stand_in.ask("/review the timer", (REVIEW,))
    assert engine.referenced == [("ses_1", (REVIEW,))]


def test_what_was_picked_goes_with_a_message_sent_now() -> None:
    stand_in, engine = app()
    asked(stand_in, "make it calm")
    stand_in.send_now("/review the timer", (REVIEW,))
    assert engine.referenced == [("ses_1", (REVIEW,))]


def test_the_picker_offers_the_projects_files_and_the_skills_there() -> None:
    from pathlib import Path
    from types import SimpleNamespace

    from osiris.harness.harness import Harness
    from tests.test_harness import GPT, HOME

    project = HOME / "Code" / "timer"
    stand_in, engine = app()
    stand_in.harness = Harness(engine, stand_in.log, GPT, directory=project)
    stand_in.programs = lambda: SimpleNamespace(files=lambda _name: [Path("README.md")])
    review = Entry("skill", "review", "review", "Review the changes")
    asked_in: list[Path] = []
    stand_in.skills = SimpleNamespace(
        skills=lambda directory: asked_in.append(directory) or [review]
    )
    stand_in.refresh_offers()
    readme = Entry("file", str(project / "README.md"), "README.md", "")
    assert stand_in.offered("@") == [readme]
    assert stand_in.offered("/") == [review]
    assert asked_in == [project]


def test_a_folder_that_is_no_program_offers_no_files_and_no_problem() -> None:
    from types import SimpleNamespace

    from osiris.harness.harness import Harness
    from osiris.programs.programs import ProgramError
    from tests.test_harness import GPT, HOME

    def no_program(name: str) -> list[object]:
        raise ProgramError(f"There is no Program called {name}")

    stand_in, engine = app()
    stand_in.harness = Harness(
        engine, stand_in.log, GPT, directory=HOME / "Code" / "notes"
    )
    stand_in.programs = lambda: SimpleNamespace(files=no_program)
    stand_in.skills = None
    stand_in.refresh_offers()
    assert stand_in.offered("@") == []
    assert stand_in.problem is None
