"""A Skin may hide a sidebar row's controls until the pointer is on the row,
but never the buttons in the menu one of them opens."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from gi.repository import Gdk, Gtk
from sidebar import Sidebar

from osiris.harness.engine import Past

from .conftest import APPS, widgets

SKINS = sorted((APPS / "harness" / "skins").glob("*.css"))
MARK = Gdk.RGBA()
MARK.parse("rgb(1,2,3)")


def hiding(sheet: Path) -> list[str]:
    """The selectors of the Skin's rules that make something invisible."""
    rules = re.findall(
        r"([^{}]+)\{([^}]*)\}", re.sub(r"/\*.*?\*/", "", sheet.read_text(), flags=re.S)
    )
    return [
        selector.strip()
        for selectors, body in rules
        if re.search(r"opacity:\s*0\s*;", body)
        for selector in selectors.split(",")
    ]


def menu_buttons() -> list[Gtk.Button]:
    widget = Sidebar(
        on_open=print, on_new=print, on_new_in=print, on_archive=print, on_delete=print
    )
    widget.show_history(
        [],
        [Past("ses_a", "Make me a calm theme", Path("/home/tester"), 1)],
        None,
        frozenset(),
        frozenset(),
    )
    more = next(w for w in widgets(widget) if isinstance(w, Gtk.MenuButton))
    return [w for w in widgets(more.get_popover()) if isinstance(w, Gtk.Button)]


@pytest.mark.parametrize("sheet", SKINS, ids=lambda s: s.stem)
def test_no_skin_hides_the_buttons_of_a_conversations_menu(sheet: Path) -> None:
    buttons = menu_buttons()
    probe = Gtk.CssProvider()
    probe.load_from_string(
        "".join(f"{s} {{ color: rgb(1,2,3); }}\n" for s in hiding(sheet))
    )
    display = Gdk.Display.get_default()
    Gtk.StyleContext.add_provider_for_display(display, probe, 900)
    try:
        hidden = [b.get_label() for b in buttons if b.get_color().equal(MARK)]
    finally:
        Gtk.StyleContext.remove_provider_for_display(display, probe)
    assert hidden == []
