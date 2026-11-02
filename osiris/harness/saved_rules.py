"""Rules saved by "Always allow here" (#181): kept by the Engine for a Project
until the person takes one back."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SavedRule:
    id: str
    action: str
    resource: str
    #: The Project the rule allows it in, where the Engine knows it.
    project: Path | None
