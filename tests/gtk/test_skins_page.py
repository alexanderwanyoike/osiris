"""Appearance's Skins section: every Skin as a card with a picture of it, the
chosen one marked, one click to wear."""

from __future__ import annotations

from pathlib import Path

from gi.repository import Gtk
from skins_page import SkinsPage

from .conftest import texts, widgets

SKINS = [
    ("osiris", "Osiris", "Osiris's own look"),
    ("colloid", "Colloid", "Vince Liuice, GPL-3.0"),
]


def rows(page: Gtk.Widget) -> dict[str, Gtk.Widget]:
    """Each Skin's card, by the name it shows."""
    cards = [w for w in widgets(page) if w.has_css_class("skin-card")]
    return {
        next(
            w.get_text()
            for w in widgets(card)
            if isinstance(w, Gtk.Label) and w.has_css_class("skin-name")
        ): card
        for card in cards
    }


def wear(page: Gtk.Widget, title: str) -> None:
    flow = next(w for w in widgets(page) if isinstance(w, Gtk.FlowBox))
    flow.emit("child-activated", rows(page)[title].get_parent())


def test_every_skin_is_listed_with_who_made_it() -> None:
    page = SkinsPage(SKINS, chosen="osiris", on_pick=lambda _name: None)
    assert list(rows(page)) == ["Osiris", "Colloid"]
    assert "Vince Liuice, GPL-3.0" in texts(rows(page)["Colloid"])


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
    wear(page, "Colloid")
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


def test_asking_osiris_wears_the_ai_star_not_a_pencil() -> None:
    skins = [*SKINS, ("mine", "Mine", "You, GPL-3.0")]
    page = SkinsPage(skins, "osiris", lambda _n: None, mine={"mine"})
    assert buttons(page, "Ask Osiris to change it")[0].get_icon_name() == (
        "osiris-ask-symbolic"
    )


def test_a_persons_own_skin_can_be_edited_by_hand() -> None:
    edited: list[str] = []
    skins = [*SKINS, ("mine", "Mine", "You, GPL-3.0")]
    page = SkinsPage(
        skins, "osiris", lambda _n: None, mine={"mine"}, on_edit=edited.append
    )
    edit = buttons(page, "Edit")
    assert len(edit) == 1
    assert edit[0].get_icon_name() == "document-edit-symbolic"
    edit[0].emit("clicked")
    assert edited == ["mine"]


def test_a_new_skin_can_be_created_from_the_section() -> None:
    created: list[bool] = []
    page = SkinsPage(
        SKINS, "osiris", lambda _n: None, on_create=lambda: created.append(True)
    )
    buttons(page, "New Skin")[0].emit("clicked")
    assert created == [True]


def test_a_card_shows_a_picture_of_its_skin(tmp_path: Path) -> None:
    picture = tmp_path / "colloid-dark.png"
    page = SkinsPage(
        SKINS, "osiris", lambda _n: None, previews={"colloid": str(picture)}
    )
    shown = [w for w in widgets(rows(page)["Colloid"]) if isinstance(w, Gtk.Picture)]
    assert [w.get_file().get_path() for w in shown] == [str(picture)]


def test_a_skin_without_a_picture_still_gets_a_card() -> None:
    page = SkinsPage(SKINS, "osiris", lambda _n: None)
    card = rows(page)["Osiris"]
    assert not [w for w in widgets(card) if isinstance(w, Gtk.Picture)]
    assert any(
        isinstance(w, Gtk.Image)
        and w.get_icon_name() == "preferences-desktop-appearance-symbolic"
        for w in widgets(card)
    )
