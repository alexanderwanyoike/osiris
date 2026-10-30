"""What the switcher's overlay browses: a deck of cards, one per choice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Card:
    name: str
    label: str
    detail: str


class SkinEngine(Protocol):
    def skin_choices(self) -> list[tuple[str, str, str]]: ...


class SkinDeck:
    def __init__(self, engine: SkinEngine) -> None:
        self._engine = engine

    def cards(self) -> list[Card]:
        return [
            Card(name=name, label=label, detail=credit)
            for name, label, credit in self._engine.skin_choices()
        ]
