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


def buttons(root: Gtk.Widget, tooltip: str) -> list[Gtk.Button]:
    return [
        w
        for w in widgets(root)
        if isinstance(w, Gtk.Button) and w.get_tooltip_text() == tooltip
    ]


def test_a_skinpack_can_be_opened_from_the_section() -> None:
    opened: list[bool] = []
    page = SkinsPage(
        SKINS, "osiris", lambda _n: None, on_open=lambda: opened.append(True)
    )
    buttons(page, "Open a skinpack")[0].emit("clicked")
    assert opened == [True]


def test_every_pack_can_be_exported_but_not_osiris_own() -> None:
    exported: list[str] = []
    page = SkinsPage(SKINS, "osiris", lambda _n: None, on_export=exported.append)
    export = buttons(page, "Export")
    assert len(export) == 1
    export[0].emit("clicked")
    assert exported == ["colloid"]


def test_only_a_persons_own_skins_can_be_deleted() -> None:
    deleted: list[str] = []
    skins = [*SKINS, ("mine", "Mine", "You, GPL-3.0")]
    page = SkinsPage(
        skins, "osiris", lambda _n: None, mine={"mine"}, on_delete=deleted.append
    )
    delete = buttons(page, "Delete")
    assert len(delete) == 1
    delete[0].emit("clicked")
    assert deleted == ["mine"]


def test_every_pack_can_be_duplicated_but_not_osiris_own() -> None:
    copied: list[str] = []
    page = SkinsPage(SKINS, "osiris", lambda _n: None, on_duplicate=copied.append)
    duplicate = buttons(page, "Duplicate")
    assert len(duplicate) == 1
    duplicate[0].emit("clicked")
    assert copied == ["colloid"]


def test_only_a_persons_own_skins_offer_asking_osiris_to_change_them() -> None:
    asked: list[str] = []
    skins = [*SKINS, ("mine", "Mine", "You, GPL-3.0")]
    page = SkinsPage(
        skins, "osiris", lambda _n: None, mine={"mine"}, on_change=asked.append
    )
    change = buttons(page, "Ask Osiris to change it")
    assert len(change) == 1
    change[0].emit("clicked")
    assert asked == ["mine"]
