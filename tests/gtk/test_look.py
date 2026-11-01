"""The Harness's own look stays on top of the GTK 4 user sheet, which a Skin
fills with whole-window rules; below it, a Skin's solid window background
replaces the drawer's glass."""

from __future__ import annotations

from pathlib import Path

from gi.repository import Gtk
from look import Look

from osiris.apps.user_css import UserCss


def test_the_drawers_look_outranks_the_user_sheet(tmp_path: Path) -> None:
    """A Skin's sheet redefining libadwaita's window colour leaves the
    drawer in the Theme's."""
    sheet = tmp_path / "gtk.css"
    sheet.write_text(
        "@define-color window_bg_color #ff0000;"
        " label.look-probe { color: @window_bg_color; }"
    )
    UserCss(sheet)
    Look(tmp_path, lambda: None)
    probe = Gtk.Label(css_classes=["look-probe"])
    assert probe.get_color().to_string() != "rgb(255,0,0)"


def test_code_is_drawn_in_the_themes_terminal_font(tmp_path: Path) -> None:
    look = Look(tmp_path, lambda: None)
    loaded = look._provider.to_string()
    assert "calt" in loaded and "liga" in loaded


def test_the_look_keeps_the_theme_it_loaded(tmp_path: Path) -> None:
    """For what draws itself from the Theme, such as a terminal."""
    look = Look(tmp_path, lambda: None)
    assert "background" in look.theme["colors"]
