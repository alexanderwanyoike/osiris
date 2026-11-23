"""The port every Media provider's pictures come through."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ImageMaker(Protocol):
    def make(self, description: str, model: str | None = None) -> bytes:
        """One picture of ``description``, as an image file's bytes, by ``model``
        or the default one."""
        ...
