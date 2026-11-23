"""The port a Media provider's list of image models comes through."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from osiris.harness.media.image_model import ImageModel


@runtime_checkable
class ModelCatalog(Protocol):
    def search(self, words: str) -> list[ImageModel]:
        """The models on offer that match ``words``, or a selection if empty."""
        ...

    def inputs(self, model: str) -> frozenset[str]:
        """What ``model`` accepts, refused if it is not on offer."""
        ...
