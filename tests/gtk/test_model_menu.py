"""The model menu under the message box (#222): a search, about eight rows
that scroll, each model with its maker's icon, and Providers pinned below.
What it lists and in what order is osiris/harness/model_menu.py's."""

from __future__ import annotations

from model_menu import ModelMenu

from osiris.harness.accounts import ModelInfo
from osiris.harness.engine import ModelRef


def model(provider: str, name: str, family: str = "") -> ModelInfo:
    return ModelInfo(ModelRef(provider, name.lower()), name, family=family)


SOL = model("openai", "GPT-6 Sol", "gpt-6")
TERRA = model("openai", "GPT-6.1 Terra", "gpt-6.1")
FLINT = model("opencode-go", "Flint")
PICKLE = model("opencode", "Big Pickle")
MODELS = [PICKLE, FLINT, TERRA, SOL]
PROVIDERS = {
    "openai": "OpenAI",
    "opencode": "OpenCode Zen",
    "opencode-go": "OpenCode Go",
}


def menu(models: list[ModelInfo] = MODELS) -> tuple[ModelMenu, list[object]]:
    chosen: list[object] = []
    widget = ModelMenu(
        on_chosen=chosen.append,
        on_providers=lambda: chosen.append("providers"),
        on_close=lambda: chosen.append("closed"),
    )
    widget.show_models(models, SOL.ref, PROVIDERS)
    return widget, chosen


def listed(widget: ModelMenu) -> list[str]:
    return [row.model.name for row in widget.list]


def test_typing_in_the_search_narrows_the_models() -> None:
    widget, _ = menu()
    widget.search.set_text("terra")
    assert listed(widget) == ["GPT-6.1 Terra"]
    widget.search.set_text("")
    assert listed(widget) == ["GPT-6 Sol", "GPT-6.1 Terra", "Flint", "Big Pickle"]
