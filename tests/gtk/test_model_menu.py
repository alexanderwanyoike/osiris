"""The model menu under the message box (#222): a search, about eight rows
that scroll, each model with its maker's icon, and Providers pinned below.
What it lists and in what order is osiris/harness/model_menu.py's."""

from __future__ import annotations

from gi.repository import Gtk
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


def test_about_eight_rows_show_before_the_list_scrolls() -> None:
    many = [model("openai", f"GPT-{n}", "gpt") for n in range(26)]
    widget, _ = menu(many)
    row = widget.list.get_row_at_index(0)
    one = row.measure(Gtk.Orientation.VERTICAL, -1)[1]
    shown = widget.card.measure(Gtk.Orientation.VERTICAL, -1)[1]
    assert 7 * one <= shown <= 9 * one
    assert widget.list.measure(Gtk.Orientation.VERTICAL, -1)[1] > shown


def test_providers_and_accounts_is_pinned_below_the_list() -> None:
    """Outside the scroll, so it is always there, however many models."""
    widget, chosen = menu()
    assert widget.providers.get_parent() is widget
    assert widget.get_last_child() is widget.providers
    widget.providers.emit("clicked")
    assert chosen == ["providers"]
