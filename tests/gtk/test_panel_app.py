"""The App fills the Conversation panel (#169) from the Harness, the Engine and
the Conversation on screen."""

from __future__ import annotations

from types import SimpleNamespace

from osiris.harness.accounts import ModelInfo
from osiris.harness.connectors import State
from osiris.harness.context import ContextUse
from osiris.harness.engine import ModelRef
from osiris.harness.harness import Harness
from osiris.harness.log import Change
from tests.test_harness import GPT, HOME

from .test_side_by_side import app


class Panel:
    def __init__(self) -> None:
        self.where: list[tuple[str, str]] = []
        self.connectors: list[dict[str, State]] = []
        self.context: list[object] = []
        self.changes: list[list[tuple[int, str, int]]] = []

    def show_where(self, project: str, branch: str) -> None:
        self.where.append((project, branch))

    def show_connectors(self, states: dict[str, State]) -> None:
        self.connectors.append(states)

    def show_context(self, _shared: object, used: int, window: int) -> None:
        self.context.append((used, window))

    def show_no_context(self) -> None:
        self.context.append("nothing")

    def show_changes(
        self, changed: list[tuple[int, str, int]], _on_open: object
    ) -> None:
        self.changes.append(changed)


def test_the_panel_shows_where_it_runs_its_connectors_context_and_changes() -> None:
    stand_in, engine = app()
    project = HOME / "Code" / "timer"
    stand_in.harness = Harness(engine, stand_in.log, GPT, directory=project)
    stand_in.harness.ask("make it calm")
    stand_in.models = SimpleNamespace(default=GPT)
    stand_in.drawer.conversation_panel = panel = Panel()
    calm = stand_in.conversation.asked("make it calm")
    calm.changes.append(
        Change(
            "Timer: Calmer colours",
            {"action": "revert_commit", "name": "timer", "commit": "abc"},
            "timer",
        )
    )
    stand_in.conversation.asked("what is a theme?")
    stand_in.servers = SimpleNamespace(
        connector_states=lambda _d: {
            "wiki": State("connected"),
            "osiris": State("connected"),
        }
    )
    stand_in.contexts = SimpleNamespace(
        context_use=lambda _s: ContextUse({"questions": 10}, used=5000)
    )
    stand_in.accounts = SimpleNamespace(
        models=lambda: [ModelInfo(ModelRef(GPT.provider, GPT.model), "GPT", 100_000)]
    )
    stand_in.update_panel()
    assert panel.where[-1][0] == "timer"
    assert panel.connectors == [{"wiki": State("connected")}]
    assert panel.context == [(5000, 100_000)]
    assert panel.changes == [[(0, "make it calm", 1)]]


def test_a_panel_asked_for_before_a_conversation_reopens_is_filled_for_it() -> None:
    stand_in, _engine = app()
    stand_in.models = SimpleNamespace(default=GPT)
    stand_in.drawer.conversation_panel = panel = Panel()
    asked: list[object] = []
    stand_in.contexts = SimpleNamespace(
        context_use=lambda s: asked.append(s) or ContextUse({}, used=10)
    )
    stand_in.accounts = SimpleNamespace(models=lambda: [])

    def reopened_meanwhile(work, done):
        result = work()
        if not asked:
            stand_in.harness.resume("ses_past")
        done(result)

    stand_in.background = reopened_meanwhile
    stand_in.update_panel()
    assert asked == ["ses_past"]
    assert panel.connectors


def test_a_conversation_with_nothing_asked_clears_the_context_card() -> None:
    stand_in, _engine = app()
    stand_in.models = SimpleNamespace(default=GPT)
    stand_in.drawer.conversation_panel = panel = Panel()
    stand_in.contexts = SimpleNamespace(context_use=lambda _s: None)
    stand_in.accounts = SimpleNamespace(models=lambda: [])
    stand_in.update_panel()
    assert panel.context == ["nothing"]


def test_the_panel_follows_the_conversation_on_screen_into_its_project() -> None:
    """The history's pass moves a Conversation that made a Program while it
    still answers; the Where card says so at once, not when the answer ends
    (#221)."""
    stand_in, _engine = app()
    del stand_in.load_history
    stand_in.harness.ask("build me a timer")
    stand_in.log.write("changed", session="ses_1", program="pomodoro")
    stand_in.files.directories.add(HOME / "Code" / "pomodoro")
    stand_in.models = SimpleNamespace(default=GPT)
    stand_in.contexts = stand_in.accounts = None
    stand_in.drawer.show_history = lambda *_groups: None
    stand_in.drawer.conversation_panel = panel = Panel()
    stand_in.load_history()
    assert panel.where[-1] == ("pomodoro", "")


def test_a_question_with_nothing_to_show_is_not_listed_on_the_changes_card() -> None:
    """Making a Program, or a Theme, has no commit of its own to open; the
    card lists only what the Changes tab can show (#219)."""
    stand_in, _engine = app()
    stand_in.models = SimpleNamespace(default=GPT)
    stand_in.contexts = stand_in.accounts = None
    stand_in.drawer.conversation_panel = panel = Panel()
    made = stand_in.conversation.asked("build me a habit tracker")
    made.changes.append(
        Change(
            "Made Daily Habits",
            {"action": "trash_program", "name": "daily-habits"},
            "daily-habits",
        )
    )
    stand_in.update_panel()
    assert panel.changes == [[]]


def test_the_changes_card_counts_what_the_changes_tab_shows() -> None:
    """A theme applied beside a commit is no second change on the tab."""
    stand_in, _engine = app()
    stand_in.models = SimpleNamespace(default=GPT)
    stand_in.contexts = stand_in.accounts = None
    stand_in.drawer.conversation_panel = panel = Panel()
    calm = stand_in.conversation.asked("make it calm")
    calm.changes += [
        Change("Applied Nord", None),
        Change(
            "Timer: Calmer colours",
            {"action": "revert_commit", "name": "timer", "commit": "abc"},
            "timer",
        ),
    ]
    stand_in.update_panel()
    assert panel.changes == [[(0, "make it calm", 1)]]
