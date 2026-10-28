"""The Skin editor: rename a Skin and choose its style, icons, cursor and font,
each shown as it would look."""

from __future__ import annotations

from pathlib import Path

import pytest
from gi.repository import Gtk
from skin_editor import Choice, SkinEditor

from .conftest import widgets

STYLES = [("colloid", "Colloid", None), ("graphite", "Graphite", None)]
ICONS = ["Adwaita", "Papirus"]
CURSORS = ["Adwaita", "Bibata"]


def editor(saved: list[Choice], **overrides: object) -> SkinEditor:
    given: dict[str, object] = {
        "label": "Sharp",
        "styles": STYLES,
        "style": "colloid",
        "icon_sets": ICONS,
        "icons": None,
        "cursor_sets": CURSORS,
        "cursor_pictures": {},
        "cursor": None,
        "font": None,
        "on_save": saved.append,
    }
    given.update(overrides)
    return SkinEditor(**given)


def section(dialog: SkinEditor, title: str) -> Gtk.FlowBox:
    return next(
        w
        for w in widgets(dialog.get_child())
        if isinstance(w, Gtk.FlowBox) and w.get_name() == title
    )


def choose(flow: Gtk.FlowBox, label: str) -> None:
    for child in widgets(flow):
        if isinstance(child, Gtk.FlowBoxChild) and any(
            isinstance(w, Gtk.Label) and w.get_text() == label for w in widgets(child)
        ):
            flow.select_child(child)
            return
    raise AssertionError(f"no {label} to choose")


def chosen(flow: Gtk.FlowBox) -> list[str]:
    return [
        next(w.get_text() for w in widgets(child) if isinstance(w, Gtk.Label))
        for child in flow.get_selected_children()
    ]


def save(dialog: SkinEditor) -> None:
    next(
        w
        for w in widgets(dialog.get_child())
        if isinstance(w, Gtk.Button) and w.get_label() == "Save"
    ).emit("clicked")


def test_saving_unchanged_gives_back_what_the_skin_has() -> None:
    saved: list[Choice] = []
    dialog = editor(saved)
    save(dialog)
    assert saved == [Choice("Sharp", "colloid", None, None, None)]


def test_the_skin_can_be_renamed() -> None:
    saved: list[Choice] = []
    dialog = editor(saved)
    name = next(
        w
        for w in widgets(dialog.get_child())
        if isinstance(w, Gtk.Editable) and w.get_text() == "Sharp"
    )
    name.set_text("Sharp Night")
    save(dialog)
    assert saved[0].label == "Sharp Night"


def test_the_skins_style_is_chosen_and_another_can_be() -> None:
    saved: list[Choice] = []
    dialog = editor(saved)
    assert chosen(section(dialog, "Style")) == ["Colloid"]
    choose(section(dialog, "Style"), "Graphite")
    save(dialog)
    assert saved[0].style == "graphite"


def test_icon_sets_are_shown_by_their_icons_and_the_themes_choice_first() -> None:
    saved: list[Choice] = []
    dialog = editor(saved)
    icons = section(dialog, "Icons")
    assert chosen(icons) == ["Theme's choice"]
    papirus = next(
        child
        for child in widgets(icons)
        if isinstance(child, Gtk.FlowBoxChild)
        and any(
            isinstance(w, Gtk.Label) and w.get_text() == "Papirus"
            for w in widgets(child)
        )
    )
    assert len([w for w in widgets(papirus) if isinstance(w, Gtk.Image)]) >= 4
    choose(icons, "Papirus")
    save(dialog)
    assert saved[0].icons == "Papirus"


def test_cursor_sets_are_shown_by_their_pointers(tmp_path: Path) -> None:
    saved: list[Choice] = []
    pointer = tmp_path / "bibata-pointer.png"
    dialog = editor(saved, cursor="Bibata", cursor_pictures={"Bibata": [str(pointer)]})
    cursors = section(dialog, "Cursor")
    assert chosen(cursors) == ["Bibata"]
    files = [
        w.get_file().get_path()
        for w in widgets(cursors)
        if isinstance(w, Gtk.Picture) and w.get_file() is not None
    ]
    assert files == [str(pointer)]
    choose(cursors, "Theme's choice")
    save(dialog)
    assert saved[0].cursor is None


def test_a_font_can_be_chosen_or_left_to_the_theme() -> None:
    saved: list[Choice] = []
    dialog = editor(saved, font="Inter 11")
    keep = next(
        w
        for w in widgets(dialog.get_child())
        if isinstance(w, Gtk.CheckButton) and w.get_label() == "Theme's font"
    )
    assert keep.get_active() is False
    save(dialog)
    keep.set_active(True)
    save(dialog)
    assert [choice.font for choice in saved] == ["Inter 11", None]


def test_the_skin_can_still_be_opened_in_the_code_editor() -> None:
    opened: list[bool] = []
    dialog = editor([], on_code=lambda: opened.append(True))
    next(
        w
        for w in widgets(dialog.get_child())
        if isinstance(w, Gtk.Button) and w.get_label() == "Open in Code"
    ).emit("clicked")
    assert opened == [True]


def test_the_themes_choice_shows_the_themes_own_cursor(tmp_path: Path) -> None:
    """Pictures under the empty name are the Theme's cursor."""
    pointer = tmp_path / "theme-pointer.png"
    dialog = editor([], cursor_pictures={"": [str(pointer)]})
    first = section(dialog, "Cursor").get_child_at_index(0)
    files = [
        w.get_file().get_path()
        for w in widgets(first)
        if isinstance(w, Gtk.Picture) and w.get_file() is not None
    ]
    assert files == [str(pointer)]


def test_downloaded_icons_cursors_and_fonts_can_be_added() -> None:
    added: list[str] = []
    dialog = editor(
        [],
        on_add_icons=lambda: added.append("icons"),
        on_add_cursors=lambda: added.append("cursors"),
        on_add_fonts=lambda: added.append("fonts"),
    )
    for tooltip in ("Add an icon set", "Add a cursor set", "Add fonts"):
        next(
            w
            for w in widgets(dialog.get_child())
            if isinstance(w, Gtk.Button) and w.get_tooltip_text() == tooltip
        ).emit("clicked")
    assert added == ["icons", "cursors", "fonts"]


@pytest.mark.parametrize("style", [None, "gone"])
def test_a_style_not_on_offer_is_shown_as_it_is_and_kept(style: str | None) -> None:
    """Review of #134: the first style was pre-selected instead, and an
    unchanged save replaced the Skin's sheets with it."""
    saved: list[Choice] = []
    dialog = editor(saved, style=style)
    assert chosen(section(dialog, "Style")) == ["As it is"]
    save(dialog)
    assert saved[0].style is None


def test_an_icon_set_or_cursor_not_installed_stays_chosen() -> None:
    saved: list[Choice] = []
    dialog = editor(saved, icons="Gone-Icons", cursor="Gone-Cursor")
    assert chosen(section(dialog, "Icons")) == ["Gone-Icons"]
    assert chosen(section(dialog, "Cursor")) == ["Gone-Cursor"]
    save(dialog)
    assert (saved[0].icons, saved[0].cursor) == ("Gone-Icons", "Gone-Cursor")


def test_the_themes_font_is_what_the_theme_uses() -> None:
    dialog = editor([], theme_font="Noto Sans 10")
    picker = next(
        w for w in widgets(dialog.get_child()) if isinstance(w, Gtk.FontDialogButton)
    )
    assert picker.get_font_desc().to_string() == "Noto Sans 10"


def test_a_failed_save_keeps_the_editor_open() -> None:
    closed: list[bool] = []
    dialog = editor([], on_save=lambda _choice: False)
    dialog.close = lambda: closed.append(True)
    save(dialog)
    assert closed == []


def test_what_is_chosen_can_be_read_without_saving() -> None:
    """Review of #136: adding an icon set reopened the editor from the
    saved Skin, losing every choice made before the Add."""
    saved: list[Choice] = []
    dialog = editor(saved)
    choose(section(dialog, "Icons"), "Papirus")
    choose(section(dialog, "Style"), "Graphite")
    assert dialog.choice() == Choice("Sharp", "graphite", "Papirus", None, None)
    assert saved == []
