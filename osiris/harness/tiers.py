"""Action tiers: how far an action of the Harness reaches (CONTEXT.md).

A look just happens and an undoable change happens with an Undo. A change that
cannot be undone asks first; no action of that tier exists yet, so the Harness
rejects anything without a tier.
"""

from __future__ import annotations

from enum import Enum


class Tier(Enum):
    LOOK = "look"
    UNDOABLE = "undoable"
