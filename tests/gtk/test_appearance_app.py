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


def test_a_pair_card_switches_between_its_light_and_dark_themes() -> None:
    """#266: one card per pair, with a switch between its halves."""
    from .conftest import widgets

    van = {"name": "van", "label": "Van", "dark": False, "pair": "van-night"}
    night = {"name": "van-night", "label": "Van Night", "dark": True, "pair": "van"}
    picked: list[dict[str, object]] = []
    card = appearance().ThemeCard(
        van, picked.append, False, lambda *_: None, partner=night, dark=False
    )
    switch = next(w for w in widgets(card) if isinstance(w, Gtk.Switch))
    card.button.emit("clicked")
    switch.set_active(True)
    card.button.emit("clicked")
    assert [theme["name"] for theme in picked] == ["van", "van-night", "van-night"]


def test_a_pair_cards_switch_leaves_its_name_readable() -> None:
    """Filming #266: the switch sat over the first word of the pair's name."""
    from .conftest import settle, widgets

    van = {"name": "van", "label": "Mystery Machine", "dark": False, "pair": "n"}
    night = {"name": "n", "label": "Mystery Machine Night", "dark": True}
    card = appearance().ThemeCard(
        van, lambda _t: None, False, lambda *_: None, partner=night
    )
    window = Gtk.Window(child=card)
    window.present()
    settle(lambda: card.get_width() > 0)
    switch = next(w for w in widgets(card) if isinstance(w, Gtk.Switch))
    name = next(w for w in widgets(card) if "theme-name" in w.get_css_classes())
    switch_box = switch.compute_bounds(card)[1]
    name_box = name.compute_bounds(card)[1]
    window.destroy()
    assert not switch_box.intersection(name_box)[0]


def test_the_dark_halfs_card_wears_the_dark_half_when_the_switch_says_dark() -> None:
    """Review of #271: among dark Themes only the dark half shows, and its
    card applied the light Theme."""
    night = {"name": "van-night", "label": "Van Night", "dark": True, "pair": "van"}
    van = {"name": "van", "label": "Van", "dark": False, "pair": "van-night"}
    picked: list[dict[str, object]] = []
    card = appearance().ThemeCard(
        night, picked.append, False, lambda *_: None, partner=van, dark=True
    )
    card.button.emit("clicked")
    assert [theme["name"] for theme in picked] == ["van-night"]
