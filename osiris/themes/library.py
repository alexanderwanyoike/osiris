"""Finding a theme among many."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import Enum
from typing import Any

#: A theme document, as loaded from its JSON file.
Theme = Mapping[str, Any]


class Family(Enum):
    RED = "Reds"
    ORANGE = "Oranges"
    YELLOW = "Yellows"
    GREEN = "Greens"
    TEAL = "Teals"
    BLUE = "Blues"
    PURPLE = "Purples"
    PINK = "Pinks"
    NEUTRAL = "Neutrals"


class Filter(Enum):
    ALL = "all"
    DARK = "dark"
    LIGHT = "light"
    MINE = "mine"


def family_of(theme: Theme) -> Family:
    raise NotImplementedError


def arrange(
    themes: Iterable[Theme],
    query: str = "",
    chosen: Filter = Filter.ALL,
    favourites: frozenset[str] | set[str] = frozenset(),
    mine: frozenset[str] | set[str] = frozenset(),
) -> list[tuple[str, list[Theme]]]:
    raise NotImplementedError
