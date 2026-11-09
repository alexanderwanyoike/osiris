"""What the model menu lists, in what order, and whose icon each model wears
(#222); the menu itself only draws it."""

from __future__ import annotations

from osiris.harness.model_menu import maker_of


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
