"""The Harness's model settings: plain text the person can read and edit."""

from __future__ import annotations

from osiris.harness.engine import ModelRef
from osiris.harness.settings import Models, read_models


def test_the_default_model_is_read_as_provider_slash_model() -> None:
    assert read_models("default = openai/gpt-5.5\n") == Models(
        default=ModelRef("openai", "gpt-5.5"), fallback=None
    )


def test_a_fallback_model_is_read_beside_the_default() -> None:
    models = read_models("default = openai/gpt-5.5\nfallback = opencode-go/kimi-k2\n")
    assert models.fallback == ModelRef("opencode-go", "kimi-k2")
