"""What the switcher's overlay shows: Themes on Super+T, Skins on Super+S."""

from __future__ import annotations

from typing import Any

from osiris.apps.decks import SkinDeck

ROSE_PINE: dict[str, Any] = {
    "name": "rose-pine",
    "label": "Rose Pine",
    "preview": "/previews/rose-pine.png",
    "colors": {"background": "#191724", "warning": "#f6c177"},
}


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
