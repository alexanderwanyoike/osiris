"""What the switcher's overlay shows: Themes on Super+T, Skins on Super+S."""

from __future__ import annotations

from typing import Any

from osiris.apps.decks import SkinDeck, ThemeDeck

PALETTE = {
    "background": "#191724",
    "surface": "#1f1d2e",
    "accent": "#2f6fd6",
    "accentMuted": "#26233a",
    "success": "#9ccfd8",
    "warning": "#f6c177",
    "danger": "#eb6f92",
}
ROSE_PINE: dict[str, Any] = {
    "name": "rose-pine",
    "label": "Rose Pine",
    "preview": "/previews/rose-pine.png",
    "colors": PALETTE,
}
EMBER: dict[str, Any] = {
    "name": "ember",
    "label": "Ember",
    "dark": False,
    "colors": {**PALETTE, "accent": "#e8762c"},
}


class Themes:
    def __init__(self) -> None:
        self.applied: list[str] = []

    def all_themes(self) -> list[dict[str, Any]]:
        return [ROSE_PINE, EMBER]

    def favourites(self) -> set[str]:
        return {"rose-pine"}

    def current(self) -> str | None:
        return "ember"

    def wallpaper_for(self, theme: dict[str, Any]) -> str:
        return f"/walls/{theme['name']}.png"

    def missing_packages(self, theme: dict[str, Any]) -> list[str]:
        return ["ttf-iosevka", "papirus"] if theme["name"] == "ember" else []

    def apply(self, name: str) -> list[str]:
        self.applied.append(name)
        return []


class Skins:
    def __init__(self) -> None:
        self.worn: list[str] = []
        self.drawn: list[str] = []

    def skin_choices(self) -> list[tuple[str, str, str]]:
        return [
            ("osiris", "Osiris", "Osiris's own look"),
            ("colloid", "Colloid", "Vince Liuice, GPL-3.0"),
            ("old-forest", "Old Forest", "You"),
        ]

    def own_skins(self) -> set[str]:
        return {"old-forest"}

    def chosen_skin(self) -> str:
        return "colloid"

    def skin_pictures(self) -> dict[str, str]:
        return {"colloid": "/cache/colloid.png"}

    def current_theme(self) -> dict[str, Any]:
        return ROSE_PINE

    def wallpaper_for(self, theme: dict[str, Any]) -> str:
        return f"/walls/{theme['name']}.png"

    def set_skin(self, name: str) -> list[str]:
        self.worn.append(name)
        return []

    def stale_skin_pictures(self) -> list[str]:
        return ["osiris", "old-forest"]

    def draw_skin_picture(self, name: str) -> str:
        self.drawn.append(name)
        return f"/cache/{name}.png"


def test_every_skin_is_a_card_saying_who_made_it() -> None:
    cards = SkinDeck(Skins()).cards()
    assert [(c.name, c.label, c.detail) for c in cards] == [
        ("osiris", "Osiris", "Osiris's own look"),
        ("colloid", "Colloid", "Vince Liuice, GPL-3.0"),
        ("old-forest", "Old Forest", "You"),
    ]


def test_the_persons_own_skins_are_headed_apart_from_the_rest() -> None:
    cards = SkinDeck(Skins()).cards()
    assert [c.section for c in cards] == ["Skins", "Skins", "Your Skins"]


def test_a_skin_shows_its_picture_once_drawn_over_the_themes_wallpaper() -> None:
    cards = {c.name: c for c in SkinDeck(Skins()).cards()}
    assert cards["colloid"].pictures == ("/cache/colloid.png",)
    assert cards["osiris"].pictures == ()
    assert cards["osiris"].backdrop == ("/walls/rose-pine.png", "/previews/rose-pine.png")


def test_a_skin_card_takes_its_colours_from_the_current_theme() -> None:
    card = SkinDeck(Skins()).cards()[0]
    assert card.fill == "#191724"
    assert card.warning == "#f6c177"
    assert card.swatches == ()


def test_the_worn_skin_is_current_and_choosing_one_wears_it() -> None:
    skins = Skins()
    deck = SkinDeck(skins)
    assert deck.active() == "colloid"
    assert deck.refused(deck.cards()[2]) is None
    deck.choose("old-forest")
    assert skins.worn == ["old-forest"]


def test_skins_without_a_picture_in_this_theme_are_drawn_on_request() -> None:
    skins = Skins()
    deck = SkinDeck(skins)
    assert deck.undrawn() == ["osiris", "old-forest"]
    deck.draw("osiris")
    assert skins.drawn == ["osiris"]


def test_themes_are_cards_in_library_order_with_family_and_mode() -> None:
    cards = ThemeDeck(Themes()).cards()
    assert [(c.section, c.name, c.label, c.detail) for c in cards] == [
        ("Favourites", "rose-pine", "Rose Pine", "Blues  ·  Dark"),
        ("Oranges", "ember", "Ember", "Oranges  ·  Light"),
    ]
