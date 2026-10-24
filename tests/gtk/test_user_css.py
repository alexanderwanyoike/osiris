"""Osiris's own apps follow ~/.config/gtk-4.0/gtk.css as it changes, so a new
Theme or Skin reaches them without a restart."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from gi.repository import GLib, Gtk

from osiris.apps.user_css import UserCss


def settle(until: Callable[[], bool], seconds: float = 3.0) -> bool:
    deadline = time.monotonic() + seconds
    context = GLib.MainContext.default()
    while time.monotonic() < deadline:
        while context.pending():
            context.iteration(False)
        if until():
            return True
        time.sleep(0.02)
    return False


def test_the_sheet_is_loaded_when_followed(tmp_path: Path) -> None:
    sheet = tmp_path / "gtk.css"
    sheet.write_text("window { color: #c4a7e7; }")
    css = UserCss(sheet)
    assert "rgb(196,167,231)" in css.provider.to_string()


def test_a_rewritten_sheet_is_loaded_again(tmp_path: Path) -> None:
    sheet = tmp_path / "gtk.css"
    sheet.write_text("window { color: #c4a7e7; }")
    css = UserCss(sheet)
    sheet.write_text("window { color: #907aa9; }")
    assert settle(lambda: "rgb(144,122,169)" in css.provider.to_string())


def test_it_outranks_the_copy_gtk_read_at_startup() -> None:
    assert UserCss.PRIORITY > Gtk.STYLE_PROVIDER_PRIORITY_USER


def test_no_sheet_means_an_empty_provider(tmp_path: Path) -> None:
    css = UserCss(tmp_path / "missing.css")
    assert css.provider.to_string().strip() == ""
