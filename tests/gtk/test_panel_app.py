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
        self.where: list[tuple[str, str, str]] = []
        self.connectors: list[dict[str, State]] = []
        self.context: list[tuple[int, int]] = []
        self.changes: list[list[tuple[int, str, int]]] = []

    def show_where(self, project: str, branch: str, model: str) -> None:
        self.where.append((project, branch, model))

    def show_connectors(self, states: dict[str, State]) -> None:
        self.connectors.append(states)

    def show_context(self, _shared: object, used: int, window: int) -> None:
        self.context.append((used, window))

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
    calm.changes.append(Change("Applied Nord", None))
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
