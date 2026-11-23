"""The port every media Provider's pictures come through."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ImageMaker(Protocol):
    def make(self, description: str) -> bytes:
        """One picture of ``description``, as an image file's bytes."""
        ...
