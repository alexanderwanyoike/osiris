"""What a Media provider says about running one image model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    #: Where it runs, which can differ from its id in the catalog.
    path: str
    inputs: frozenset[str]
    #: What to send as its image size; None leaves that to the model.
    size: object = None
