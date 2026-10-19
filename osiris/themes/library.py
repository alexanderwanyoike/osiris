"""Finding a theme among many.

Appearance and the theme switcher both show the same library: favourites
first, then themes grouped by the family of their accent colour, in the order
of the colour wheel, narrowed by a search and a filter.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import Enum
from typing import Any

from osiris.model.colour import Colour

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


#: Where each family starts on the hue wheel, in degrees; it runs to the next.
#: Yellow starts at 40 rather than 45 so amber and gold read as yellow.
HUE_STARTS: tuple[tuple[float, Family], ...] = (
    (15.0, Family.ORANGE),
    (40.0, Family.YELLOW),
    (70.0, Family.GREEN),
    (160.0, Family.TEAL),
    (200.0, Family.BLUE),
    (255.0, Family.PURPLE),
    (300.0, Family.PINK),
    (345.0, Family.RED),
)

#: Below this saturation an accent is a grey, whatever its hue.
NEUTRAL_BELOW = 0.15


def family_of(theme: Theme) -> Family:
    """The family of a theme's accent colour."""
    hue, _, saturation = Colour(theme["colors"]["accent"]).hls
    if saturation < NEUTRAL_BELOW:
        return Family.NEUTRAL
    degrees = hue * 360.0
    family = Family.RED
    for start, candidate in HUE_STARTS:
        if degrees >= start:
            family = candidate
    return family


def _label(theme: Theme) -> str:
    return str(theme.get("label") or theme["name"])


def _shown(
    theme: Theme, query: str, chosen: Filter, mine: frozenset[str] | set[str]
) -> bool:
    if chosen is Filter.DARK and not theme.get("dark", True):
        return False
    if chosen is Filter.LIGHT and theme.get("dark", True):
        return False
    if chosen is Filter.MINE and theme["name"] not in mine:
        return False
    needle = query.strip().lower()
    haystack = f"{_label(theme)} {theme['name']} {family_of(theme).value}".lower()
    return needle in haystack


def arrange(
    themes: Iterable[Theme],
    query: str = "",
    chosen: Filter = Filter.ALL,
    favourites: frozenset[str] | set[str] = frozenset(),
    mine: frozenset[str] | set[str] = frozenset(),
) -> list[tuple[str, list[Theme]]]:
    """The sections to show, each a title and its themes, alphabetically.

    Favourites come first and are not repeated under their family; empty
    sections are left out, so a search with no match gives none.
    """
    shown = sorted(
        (t for t in themes if _shown(t, query, chosen, mine)),
        key=lambda t: _label(t).lower(),
    )
    sections: list[tuple[str, list[Theme]]] = []
    starred = [t for t in shown if t["name"] in favourites]
    if starred:
        sections.append(("Favourites", starred))
    for family in Family:
        members = [
            t for t in shown if t["name"] not in favourites and family_of(t) is family
        ]
        if members:
            sections.append((family.value, members))
    return sections
