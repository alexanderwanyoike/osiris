#!/usr/bin/env python3
"""Osiris switcher - Super+T for Themes, Super+S for Skins; browse with the
arrows, Enter applies or wears.

A full-screen carousel over a blurred backdrop: the focused card large in the
middle, its neighbours smaller and fainter either side, sliding as you browse.
Nothing is applied until Enter, so browsing is free; Escape, or a click
outside the cards, leaves things as they were. Themes come in the library's
order (osiris/themes/library.py): favourites first, then colour families round
the wheel. Skins come as Appearance lists them, each pictured in the current
Theme.

The app stays resident so the overlay opens at once. It is started at login,
or by D-Bus on first use, with --gapplication-service, and the keys run
`gapplication action dev.osiris.Switcher show` (or `show-skins`), which costs
no Python start.
"""
import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
# runpy does not put a script's own folder on the path, and the overlay
# lives beside it.
sys.path.insert(0, HERE)
for candidate in (os.path.join(REPO, "shell", "themes"),
                  "/usr/share/osiris/themes"):
    if os.path.isdir(candidate):
        sys.path.insert(0, candidate)
        break
for candidate in ("/usr/share/osiris/lib", REPO):
    if os.path.isdir(os.path.join(candidate, "osiris")):
        sys.path.insert(0, candidate)
        break

import engine  # noqa: E402

from osiris.apps.decks import SkinDeck, ThemeDeck  # noqa: E402
from osiris.apps.user_css import UserCss  # noqa: E402
from osiris.platform import RealFileSystem  # noqa: E402
from osiris.provision.upgrade import Upgrade  # noqa: E402
from overlay import Window  # noqa: E402

APP_ID = "dev.osiris.Switcher"

CSS = b"window.switcher { background: transparent; }"


#: Seconds between looks at whether Osiris was upgraded under the Switcher.
UPGRADE_POLL = 10


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.window: Window | None = None
        self.upgrade = Upgrade(RealFileSystem())
        self.themes = ThemeDeck(engine)
        self.skins = SkinDeck(engine)
        for action, deck in (("show", self.themes), ("show-skins", self.skins)):
            show = Gio.SimpleAction.new(action, None)
            show.connect("activate", lambda *_, deck=deck: self.show_switcher(deck))
            self.add_action(show)

    def do_startup(self):
        Adw.Application.do_startup(self)
        # Resident: closing the overlay hides it, and the process waits for
        # the next key with its images already decoded.
        self.hold()
        display = Gdk.Display.get_default()
        if display is not None:
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS)
            # Above the user sheet, where a Skin's libadwaita rules land and
            # would otherwise paint the window over the desktop.
            Gtk.StyleContext.add_provider_for_display(
                display, provider, UserCss.PRIORITY + 1)
        self.window = Window(self, self.themes)
        # Warm the cards around the current theme before anyone asks.
        self.window.carousel.load()
        GLib.timeout_add_seconds(UPGRADE_POLL, self._restart_if_upgraded)

    def _restart_if_upgraded(self) -> bool:
        """Quit once Osiris is upgraded under it and the overlay is put away;
        D-Bus starts the new code on the next key."""
        in_use = self.window is not None and self.window.get_visible()
        if not self.upgrade.restart_due(in_use=in_use):
            return GLib.SOURCE_CONTINUE
        self.quit()
        return GLib.SOURCE_REMOVE

    def do_activate(self):
        self.show_switcher(self.themes)

    def show_switcher(self, deck) -> None:
        if self.window is not None:
            self.window.show_switcher(deck)


if __name__ == "__main__":
    sys.exit(Application().run(sys.argv))
