"""The port every Media provider's pictures come through."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ImageMaker(Protocol):
    def make(self, description: str, model: str) -> bytes:
        """One picture of ``description`` by ``model``, as an image file's bytes."""
        ...
