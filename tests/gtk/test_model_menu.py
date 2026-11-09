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


def test_each_model_leads_with_its_makers_icon_or_a_monogram() -> None:
    """A maker with no icon Osiris ships, or none known, gets a monogram, as
    a Provider without a logo does on the Providers page."""
    nemotron = model("opencode", "Nemotron 3", "nemotron")
    widget, _ = menu([SOL, nemotron, FLINT])
    # In the menu's order: Flint's OpenCode Go is a featured Provider.
    gpt, flint, nvidia = [row.get_child().get_first_child() for row in widget.list]
    assert gpt.get_icon_name() == "osiris-provider-openai-symbolic"
    assert nvidia.get_icon_name() == "osiris-maker-nvidia-symbolic"
    assert flint.get_label() == "F"
    assert flint.has_css_class("harness-monogram")


def test_each_model_names_its_provider_in_a_quieter_style() -> None:
    """One model can come through two Providers."""
    widget, _ = menu([SOL])
    shown = widget.list.get_row_at_index(0).get_child().get_last_child()
    assert shown.get_label() == "OpenAI"
    assert shown.has_css_class("dim-label")
