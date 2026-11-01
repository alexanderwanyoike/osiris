"""Action tiers: how far one of the Osiris tools reaches (CONTEXT.md).

A hint on the tool for the model, not a decision: the Engine's permission
rules decide what asks (ADR 0020).
"""

from __future__ import annotations

from enum import Enum


class Tier(Enum):
    LOOK = "look"
    UNDOABLE = "undoable"
