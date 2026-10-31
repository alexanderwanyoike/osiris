"""Osiris's libadwaita apps follow the active Theme's light or dark, whoever
changes the Theme: the switcher, the Harness, or the app itself."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from gi.repository import Adw, Gio, GLib

from osiris.apps.theme_scheme import ThemeScheme

THEMES = {"rose-pine": {"dark": True}, "rose-pine-dawn": {"dark": False}}


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


def scheme() -> Adw.ColorScheme:
    return Adw.StyleManager.get_default().get_color_scheme()


def test_the_scheme_starts_as_the_active_themes(tmp_path: Path) -> None:
    record = tmp_path / "theme"
    record.write_text("rose-pine-dawn\n")
    ThemeScheme(record, THEMES.__getitem__)
    assert scheme() == Adw.ColorScheme.FORCE_LIGHT


def test_a_theme_changed_elsewhere_is_followed(tmp_path: Path) -> None:
    record = tmp_path / "theme"
    record.write_text("rose-pine-dawn\n")
    following = ThemeScheme(record, THEMES.__getitem__)
    record.write_text("rose-pine\n")
    assert settle(lambda: scheme() == Adw.ColorScheme.FORCE_DARK)
    assert following is not None


def test_no_record_means_dark(tmp_path: Path) -> None:
    Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
    ThemeScheme(tmp_path / "missing", THEMES.__getitem__)
    assert scheme() == Adw.ColorScheme.FORCE_DARK


def test_an_unknown_theme_means_dark(tmp_path: Path) -> None:
    record = tmp_path / "theme"
    record.write_text("gone\n")
    Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
    ThemeScheme(record, THEMES.__getitem__)
    assert scheme() == Adw.ColorScheme.FORCE_DARK


def test_a_theme_that_is_not_an_object_means_dark(tmp_path: Path) -> None:
    """Review of #135: a Theme file holding a list raised AttributeError."""
    record = tmp_path / "theme"
    record.write_text("listed\n")
    Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
    ThemeScheme(record, lambda _name: ["not", "a", "theme"])
    assert scheme() == Adw.ColorScheme.FORCE_DARK


def test_a_record_still_being_written_is_not_followed(tmp_path: Path) -> None:
    """Review of #135: every write event was followed, and a record caught
    truncated but not yet written read as no Theme, so a light Theme
    flashed dark."""
    record = tmp_path / "theme"
    record.write_text("rose-pine-dawn\n")
    following = ThemeScheme(record, THEMES.__getitem__)
    record.write_text("")
    following._monitor.emit(
        "changed",
        Gio.File.new_for_path(str(record)),
        None,
        Gio.FileMonitorEvent.CHANGED,
    )
    assert scheme() == Adw.ColorScheme.FORCE_LIGHT


def test_an_empty_record_keeps_the_scheme_it_has(tmp_path: Path) -> None:
    """Review of #135: an empty record read as no Theme and flashed dark."""
    record = tmp_path / "theme"
    record.write_text("rose-pine-dawn\n")
    following = ThemeScheme(record, THEMES.__getitem__)
    record.write_text("")
    following.follow()
    assert scheme() == Adw.ColorScheme.FORCE_LIGHT
