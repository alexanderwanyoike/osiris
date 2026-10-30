"""What the switcher's overlay browses: a deck of cards, one per choice."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

Theme = Mapping[str, Any]


@dataclass(frozen=True)
class Card:
    name: str
    label: str
    section: str
    detail: str
    #: Images to draw the card with, the best first; the first that loads wins.
    pictures: tuple[str, ...]
    backdrop: tuple[str, ...]
    #: Colours shown on the card as dots.
    swatches: tuple[str, ...]
    #: The card's colour until a picture has loaded.
    fill: str
    warning: str


class SkinEngine(Protocol):
    def skin_choices(self) -> list[tuple[str, str, str]]: ...
    def own_skins(self) -> set[str]: ...
    def skin_pictures(self) -> dict[str, str]: ...
    def current_theme(self) -> Theme: ...
    def wallpaper_for(self, theme: Theme) -> str: ...
    def chosen_skin(self) -> str: ...
    def set_skin(self, name: str) -> list[str]: ...
    def stale_skin_pictures(self) -> list[str]: ...
    def draw_skin_picture(self, name: str) -> str: ...


def _images(*paths: str | None) -> tuple[str, ...]:
    return tuple(path for path in paths if path)


class SkinDeck:
    def __init__(self, engine: SkinEngine) -> None:
        self._engine = engine

    def cards(self) -> list[Card]:
        mine = self._engine.own_skins()
        drawn = self._engine.skin_pictures()
        theme = self._engine.current_theme()
        colours = theme["colors"]
        backdrop = _images(self._engine.wallpaper_for(theme), theme.get("preview"))
        return [
            Card(
                name=name,
                label=label,
                section="Your Skins" if name in mine else "Skins",
                detail=credit,
                pictures=_images(drawn.get(name)),
                backdrop=backdrop,
                swatches=(),
                fill=colours["background"],
                warning=colours["warning"],
            )
            for name, label, credit in self._engine.skin_choices()
        ]

    def active(self) -> str | None:
        return self._engine.chosen_skin()

    def refused(self, _card: Card) -> str | None:
        """Why a card cannot be chosen; every Skin can."""
        return None

    def choose(self, name: str) -> None:
        self._engine.set_skin(name)

    def undrawn(self) -> list[str]:
        return self._engine.stale_skin_pictures()

    def draw(self, name: str) -> None:
        """Slow: the picture is drawn by another process."""
        self._engine.draw_skin_picture(name)
