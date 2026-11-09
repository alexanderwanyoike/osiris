"""What the model menu lists, in what order, and whose icon each model wears
(#222); the menu itself only draws it."""

from __future__ import annotations

from osiris.harness.accounts import ModelInfo
from osiris.harness.engine import ModelRef
from osiris.harness.model_menu import in_menu_order, maker_of


def model(provider: str, name: str, family: str = "") -> ModelInfo:
    return ModelInfo(ModelRef(provider, name.lower()), name, family=family)


PICKLE = model("opencode", "Big Pickle")
GROK = model("openrouter", "Grok")
FLINT = model("opencode-go", "Flint")
TERRA = model("openai", "GPT-6.1 Terra", "gpt-6.1")
SOL = model("openai", "GPT-6 Sol", "gpt-6")


def test_a_family_is_known_by_its_makers_name() -> None:
    assert maker_of("gpt-6.1") == "openai"
    assert maker_of("gpt-6.1-codex") == "openai"
    assert maker_of("nemotron") == "nvidia"
    assert maker_of("deepseek-v4") == "deepseek"
    assert maker_of("glm-5") == "zhipu"
    assert maker_of("mimo") == "xiaomi"


def test_a_family_with_no_known_maker_has_none() -> None:
    assert maker_of("big-pickle") is None
    assert maker_of("") is None
    # A prefix of a word is not the word: "gptx" is no GPT.
    assert maker_of("gptx") is None


def test_the_model_in_use_comes_first_then_the_featured_providers_then_the_rest() -> (
    None
):
    """The rest keep the Engine's order (ADR 0015 features OpenAI and
    OpenCode Go)."""
    engine_order = [PICKLE, GROK, FLINT, TERRA, SOL]
    assert in_menu_order(engine_order, SOL.ref) == [SOL, TERRA, FLINT, PICKLE, GROK]


def test_with_no_model_in_use_the_featured_providers_come_first() -> None:
    assert in_menu_order([PICKLE, TERRA], None) == [TERRA, PICKLE]
