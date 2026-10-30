"""The switcher's overlay: Super+T browses Themes, Super+S browses Skins, and
either key over the other's cards turns the overlay to its own."""

from __future__ import annotations

import time
from collections.abc import Callable

from gi.repository import GLib
from overlay import Window

from osiris.apps.decks import Card

from .conftest import now


class Deck:
    aspect = 560 / 360
    verb = "wear"

    def __init__(self, names: list[str], active: str, undrawn: tuple[str, ...] = ()):
        self.names = names
        self.current = active
        self.missing = list(undrawn)
        self.pictures: dict[str, tuple[str, ...]] = {}
        self.chosen: list[str] = []
        self.drawn: list[str] = []

    def cards(self) -> list[Card]:
        return [
            Card(
                name=name,
                label=name.title(),
                section="Skins",
                detail="",
                pictures=self.pictures.get(name, ()),
                backdrop=(),
                swatches=(),
                fill="#191724",
                warning="#f6c177",
            )
            for name in self.names
        ]

    def active(self) -> str:
        return self.current

    def refused(self, _card: Card) -> None:
        return None

    def choose(self, name: str) -> None:
        self.chosen.append(name)

    def undrawn(self) -> list[str]:
        return list(self.missing)

    def draw(self, name: str) -> None:
        self.missing.remove(name)
        self.pictures[name] = (f"/pictures/{name}.png",)
        self.drawn.append(name)


def settle(done: Callable[[], bool]) -> None:
    """Run the main loop until done, for animations and timeouts."""
    context = GLib.MainContext.default()
    deadline = time.monotonic() + 3
    while not done() and time.monotonic() < deadline:
        context.iteration(False)
        time.sleep(0.01)


def themes() -> Deck:
    return Deck(["rose-pine", "ember"], active="ember")


def skins() -> Deck:
    return Deck(["osiris", "colloid", "old-forest"], active="colloid")


def test_the_skin_switcher_opens_on_the_worn_skin() -> None:
    deck = skins()
    window = Window(None, themes(), background=now)
    window.show_switcher(deck)
    assert window.carousel.deck is deck
    assert window.carousel.focused().name == "colloid"


def test_super_s_over_the_theme_cards_turns_them_to_skins() -> None:
    window = Window(None, themes(), background=now)
    deck = skins()
    window.show_switcher(window.carousel.deck)
    settle(lambda: window.carousel.reveal == 1)
    window.show_switcher(deck)
    assert window.carousel.deck is deck
    assert window.carousel.focused().name == "colloid"


def test_skin_pictures_still_missing_are_drawn_and_shown() -> None:
    deck = Deck(["osiris", "colloid"], active="osiris", undrawn=("colloid",))
    window = Window(None, themes(), background=now)
    window.show_switcher(deck)
    assert deck.drawn == ["colloid"]
    assert window.carousel.items[1].pictures == ("/pictures/colloid.png",)


def test_enter_wears_the_focused_skin() -> None:
    deck = skins()
    window = Window(None, themes(), background=now)
    window.show_switcher(deck)
    settle(lambda: window.carousel.reveal == 1)
    window.carousel.move(1)
    window.carousel.apply()
    settle(lambda: deck.chosen != [])
    assert deck.chosen == ["old-forest"]
