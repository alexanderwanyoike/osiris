#!/usr/bin/env python3
"""Osiris theme switcher - Super+T, browse with the arrows, Enter applies.

A full-screen carousel over a blurred backdrop of the focused theme's
wallpaper: the focused theme large in the middle, its neighbours smaller and
fainter either side, sliding as you browse. Nothing is applied until Enter, so
browsing is free; Escape, or a click outside the cards, leaves things as they
were. The order is the library's (osiris/themes/library.py): favourites first,
then colour families round the wheel.

The app stays resident so the overlay opens at once. It is started at login,
or by D-Bus on first use, with --gapplication-service, and Super+T runs
`gapplication action dev.osiris.Switcher show`, which costs no Python start.
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

from osiris.apps.decks import ThemeDeck  # noqa: E402
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
        show = Gio.SimpleAction.new("show", None)
        show.connect("activate", lambda *_: self.show_switcher())
        self.add_action(show)

    def do_startup(self):
        Adw.Application.do_startup(self)
        # Resident: closing the overlay hides it, and the process waits for
        # the next Super+T with its images already decoded.
        self.hold()
        display = Gdk.Display.get_default()
        if display is not None:
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS)
            # Above the user sheet, where a Skin's libadwaita rules land and
            # would otherwise paint the window over the desktop.
            Gtk.StyleContext.add_provider_for_display(
                display, provider, UserCss.PRIORITY + 1)
        self.window = Window(self, ThemeDeck(engine))
        # Warm the cards around the current theme before anyone asks.
        self.window.carousel.load()
        GLib.timeout_add_seconds(UPGRADE_POLL, self._restart_if_upgraded)

    def _restart_if_upgraded(self) -> bool:
        """Quit once Osiris is upgraded under it and the overlay is put away;
        D-Bus starts the new code on the next Super+T."""
        in_use = self.window is not None and self.window.get_visible()
        if not self.upgrade.restart_due(in_use=in_use):
            return GLib.SOURCE_CONTINUE
        self.quit()
        return GLib.SOURCE_REMOVE

    def do_activate(self):
        self.show_switcher()

    def show_switcher(self) -> None:
        if self.window is not None:
            self.window.show_switcher()


if __name__ == "__main__":
    sys.exit(Application().run(sys.argv))
