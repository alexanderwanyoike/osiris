"""Appearance follows the user sheet and the Theme's light or dark from the
moment it starts, once, however often it is launched again."""

from __future__ import annotations

import importlib.util
from types import ModuleType

from gi.repository import Gio, Gtk

from .conftest import APPS


def appearance() -> ModuleType:
    """Appearance's main.py, under a name of its own: the Harness has one too."""
    spec = importlib.util.spec_from_file_location(
        "appearance_main", APPS / "appearance" / "main.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_user_sheet_is_followed_from_startup_not_each_activation() -> None:
    """Review of #127: each launch added another provider and monitor."""
    app = appearance().Application()
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    assert app.user_css is not None


def test_launching_again_brings_back_the_open_window() -> None:
    """A second launch made a second window over the person's desktop."""
    module = appearance()
    module.Window = lambda app: Gtk.ApplicationWindow(application=app)
    app = module.Application()
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    app.activate()
    app.activate()
    assert len(app.get_windows()) == 1
