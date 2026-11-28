"""An image model a Media provider offers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImageModel:
    id: str
    name: str
    about: str
