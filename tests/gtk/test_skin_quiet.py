"""Every Skin keeps the pencil on a question out of sight until the pointer is
on the question, and never hides the icons beside an answer's time."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from gi.repository import Gdk, Gtk
from render import TurnView

from osiris.harness.activity import Step
from osiris.harness.conversation import State, Turn
from osiris.harness.log import Change
from osiris.harness.markdown import InlineStyle

from .conftest import widgets
from .test_skin_menus import MARK, SKINS, hiding

STYLE = InlineStyle(code_foreground="#ffffff", code_background="#000000")


def icons() -> dict[str, Gtk.Button]:
    turn = Turn("tidy main.py", "Tidied.", State.DONE, message="msg_3")
    turn.steps.append(Step("edit", ("main.py",)))
    turn.changes.append(
        Change(
            "pomodoro: Tidy",
            {"action": "revert_commit", "name": "pomodoro", "commit": "abc"},
            "pomodoro",
        )
    )
    view = TurnView(
        turn,
        on_undo=lambda _t: None,
        program_card=lambda _n: Gtk.Label(),
        edit=lambda _t: None,
        try_again=lambda _t: None,
        may_go_back=lambda _t: True,
        may_try_again=lambda _t: True,
    )
    view.update(turn, STYLE, None)
    return {
        w.get_icon_name(): w
        for w in widgets(view)
        if isinstance(w, Gtk.Button) and w.get_icon_name()
    }


def hidden_by(sheet: Path) -> set[str]:
    found = icons()
    probe = Gtk.CssProvider()
    probe.load_from_string(
        "".join(f"{s} {{ color: rgb(1,2,3); }}\n" for s in hiding(sheet))
    )
    display = Gdk.Display.get_default()
    Gtk.StyleContext.add_provider_for_display(display, probe, 900)
    try:
        return {name for name, b in found.items() if b.get_color().equal(MARK)}
    finally:
        Gtk.StyleContext.remove_provider_for_display(display, probe)


@pytest.mark.parametrize("sheet", SKINS, ids=lambda s: s.stem)
def test_the_pencil_waits_for_the_pointer_and_the_icons_by_the_time_do_not(
    sheet: Path,
) -> None:
    assert hidden_by(sheet) == {"document-edit-symbolic"}
    shown = re.search(
        r"\.harness-question-row:hover\s+\.harness-quiet[^{]*\{[^}]*opacity:\s*1",
        sheet.read_text(),
    )
    assert shown is not None


@pytest.mark.parametrize("sheet", SKINS, ids=lambda s: s.stem)
def test_dividers_hide_until_the_pointer_is_on_them(sheet: Path) -> None:
    """Every resize divider in the window is unseen at rest, with room to grab,
    and shows a faint line where the pointer is."""
    text = sheet.read_text()
    rest = re.search(
        r"\.harness-drawer paned > separator[^{]*\{"
        r"[^}]*background-color:\s*transparent",
        text,
    )
    hover = re.search(r"\.harness-drawer paned > separator:hover\s*\{", text)
    assert rest is not None and hover is not None
    assert not re.search(
        r"\.harness-canvas paned > separator\s*\{[^}]*background-color:\s*alpha", text
    )
