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


def test_fresh_offers_reach_a_picker_already_open() -> None:
    from types import SimpleNamespace

    stand_in, _engine = app()
    stand_in.programs = lambda: SimpleNamespace(files=lambda _name: [])
    stand_in.skills = SimpleNamespace(skills=lambda _directory: [])
    stand_in.refresh_offers()
    assert stand_in.drawer.picker_refreshes == 1


def test_at_offers_the_projects_files_then_its_servers_and_their_resources() -> None:
    from pathlib import Path
    from types import SimpleNamespace

    from osiris.harness.connectors import State
    from osiris.harness.harness import Harness
    from tests.test_harness import GPT, HOME

    project = HOME / "Code" / "timer"
    stand_in, engine = app()
    stand_in.harness = Harness(engine, stand_in.log, GPT, directory=project)
    stand_in.programs = lambda: SimpleNamespace(files=lambda _name: [Path("README.md")])
    stand_in.skills = None
    home = Entry("resource", "wiki://home", "Home", "wiki")
    stand_in.servers = SimpleNamespace(
        connector_states=lambda _d: {"wiki": State("connected")},
        resources=lambda _d: [home],
    )
    stand_in.refresh_offers()
    assert [entry.label for entry in stand_in.offered("@")] == [
        "README.md",
        "wiki",
        "Home",
    ]


def test_the_app_keeps_connectors_in_the_engines_config_and_asks_their_state() -> None:
    from types import SimpleNamespace

    from osiris.harness.connectors import Connector, State
    from osiris.harness.harness import Harness
    from osiris.platform import FakeFileSystem
    from tests.test_harness import GPT, HOME

    project = HOME / "Code" / "timer"
    stand_in, engine = app()
    stand_in.files = FakeFileSystem()
    stand_in.harness = Harness(engine, stand_in.log, GPT, directory=project)
    asked_in: list[object] = []
    stand_in.servers = SimpleNamespace(
        connector_states=lambda d: asked_in.append(d) or {"wiki": State("connected")}
    )
    wiki = Connector("wiki", url="https://w.example/mcp")
    assert stand_in.save_connector(wiki)
    assert stand_in.read_connectors() == [wiki]
    assert stand_in.connector_states() == {"wiki": State("connected")}
    assert asked_in == [project]
    assert stand_in.remove_connector("wiki")
    assert stand_in.read_connectors() == []


def test_a_skill_turned_off_is_not_offered_under_the_slash() -> None:
    from types import SimpleNamespace

    from osiris.platform import FakeFileSystem

    stand_in, _engine = app()
    stand_in.files = FakeFileSystem()
    stand_in.programs = lambda: SimpleNamespace(files=lambda _name: [])
    review = Entry("skill", "review", "review", "Review a change")
    report = Entry("skill", "report", "report", "Report a bug")
    stand_in.skills = SimpleNamespace(skills=lambda _d: [review, report])
    assert stand_in.choose_skill("report", "off")
    stand_in.refresh_offers()
    assert stand_in.offered("/") == [review]
