"""The Harness's model settings, as plain text the person can read and edit.

    default = openai/gpt-5.5
    fallback = opencode-go/kimi-k2

The Default and Fallback models are settings, never code (CONTEXT.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from osiris.harness.engine import ModelRef


@dataclass(frozen=True)
class Models:
    default: ModelRef | None
    fallback: ModelRef | None


def read_models(text: str) -> Models:
    values = dict(
        (key.strip(), value.strip())
        for key, _, value in (line.partition("=") for line in text.splitlines())
    )
    return Models(
        default=_model(values.get("default")), fallback=_model(values.get("fallback"))
    )


def _model(text: str | None) -> ModelRef | None:
    if text is None:
        return None
    provider, _, model = text.partition("/")
    return ModelRef(provider, model)
