"""The Harness's model settings, as plain text the person can read and edit.

    default = openai/gpt-5.5
    fallback = opencode-go/kimi-k2

The Default and Fallback models are settings, never code (CONTEXT.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from osiris.harness.engine import ModelRef
from osiris.platform import FileSystem

#: Relative to the home.
MODELS_FILE = ".config/osiris/harness/models"


@dataclass(frozen=True)
class Models:
    default: ModelRef | None
    fallback: ModelRef | None


def read_models(text: str) -> Models:
    pairs = (line.partition("=") for line in text.splitlines())
    values = {key.strip(): value.strip() for key, _, value in pairs}
    return Models(
        default=_model(values.get("default")), fallback=_model(values.get("fallback"))
    )


def _model(text: str | None) -> ModelRef | None:
    provider, _, model = (text or "").partition("/")
    return ModelRef(provider, model) if provider and model else None


def write_models(models: Models) -> str:
    lines = [
        f"{key} = {ref.provider}/{ref.model}"
        for key, ref in (("default", models.default), ("fallback", models.fallback))
        if ref is not None
    ]
    return "\n".join(lines) + "\n"


def load_models(files: FileSystem, home: Path) -> Models:
    path = home / MODELS_FILE
    return read_models(files.read(path)) if files.exists(path) else Models(None, None)
