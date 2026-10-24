"""Appearance's Skins section: every Skin, the chosen one marked, one click to wear."""

from __future__ import annotations

from gi.repository import Adw, Gtk
from skins_page import SkinsPage

from .conftest import texts, widgets

SKINS = [
    ("osiris", "Osiris", "Osiris's own look"),
    ("colloid", "Colloid", "Vince Liuice, GPL-3.0"),
]


def rows(page: Gtk.Widget) -> dict[str, Adw.ActionRow]:
    return {
        row.get_title(): row for row in widgets(page) if isinstance(row, Adw.ActionRow)
    }


def test_every_skin_is_listed_with_who_made_it() -> None:
    page = SkinsPage(SKINS, chosen="osiris", on_pick=lambda _name: None)
    assert list(rows(page)) == ["Osiris", "Colloid"]
    assert "Vince Liuice, GPL-3.0" in [
        row.get_subtitle() for row in rows(page).values()
    ]


def test_only_the_chosen_skin_is_marked() -> None:
    page = SkinsPage(SKINS, chosen="colloid", on_pick=lambda _name: None)
    marked = [
        title
        for title, row in rows(page).items()
        if any(
            isinstance(w, Gtk.Image)
            and w.get_visible()
            and w.get_icon_name() == "object-select-symbolic"
            for w in widgets(row)
        )
    ]
    assert marked == ["Colloid"]


def test_choosing_a_skin_asks_to_wear_it() -> None:
    picked: list[str] = []
    page = SkinsPage(SKINS, chosen="osiris", on_pick=picked.append)
    rows(page)["Colloid"].emit("activated")
    assert picked == ["colloid"]


def test_the_section_says_what_a_skin_is() -> None:
    page = SkinsPage(SKINS, chosen="osiris", on_pick=lambda _name: None)
    assert any("colours" in text for text in texts(page) if text)
