"""The port a Media provider's list of image models comes through."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from osiris.harness.media.image_model import ImageModel
from osiris.harness.media.model_spec import ModelSpec


@runtime_checkable
class ModelCatalog(Protocol):
    def search(self, words: str) -> list[ImageModel]:
        """The models on offer that match ``words``, or a selection if empty."""
        ...

    def spec(self, model: str) -> ModelSpec:
        """How to run ``model``, refused if it is not on offer."""
        ...
