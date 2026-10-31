"""How the drawer looks: the Theme's colours and the chosen Skin, kept current.

The colours, the code scheme and the choice of Skin are decided in
osiris/harness/style.py, where they are tested. This loads them into GTK and
reloads when the Theme or the Skin changes: the theme engine records the
current Theme in a file, and the Skin is named in another, so watching both
is all a live retint needs.
"""
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import Gdk, Gio, Gtk, GtkSource  # noqa: E402

from osiris.apps.user_css import UserCss  # noqa: E402
from osiris.harness.style import (  # noqa: E402
    SCHEME_FILE,
    SCHEME_ID,
    SKIN_FILE,
    colours_css,
    inline_style,
    skin_name,
    source_scheme,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
for candidate in (REPO / "shell" / "themes", Path("/usr/share/osiris/themes")):
    if candidate.is_dir():
        sys.path.insert(0, str(candidate))
        break

import engine  # noqa: E402

FALLBACK_THEME = "osiris-obsidian"


class Look:
    #: Above the user sheet, so a Skin's whole-window rules cannot undo the glass.
    PRIORITY = UserCss.PRIORITY + 1

    def __init__(self, home: Path, changed):
        self._home = home
        self._changed = changed
        self._provider = Gtk.CssProvider()
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, self._provider, self.PRIORITY)
        self.style = None
        self.scheme: GtkSource.StyleScheme | None = None
        self._monitors = [self._watch(Path(engine.STATE)),
                          self._watch(home / SKIN_FILE)]
        self.reload()

    def _watch(self, path: Path) -> Gio.FileMonitor:
        path.parent.mkdir(parents=True, exist_ok=True)
        monitor = Gio.File.new_for_path(str(path)).monitor_file(
            Gio.FileMonitorFlags.NONE, None)
        monitor.connect("changed", self._file_changed)
        return monitor

    def _file_changed(self, _monitor, _file, _other, event) -> None:
        if event in (Gio.FileMonitorEvent.CHANGES_DONE_HINT,
                     Gio.FileMonitorEvent.CREATED, Gio.FileMonitorEvent.DELETED):
            self.reload()
            self._changed()

    def _theme(self) -> dict:
        name = engine.current() or FALLBACK_THEME
        try:
            return engine.load(name)
        except (OSError, ValueError, KeyError):
            return engine.load(FALLBACK_THEME)

    def _skin(self) -> str:
        try:
            chosen = (self._home / SKIN_FILE).read_text()
        except OSError:
            chosen = None
        name = skin_name(chosen)
        for directory in (HERE / "skins", Path("/usr/share/osiris/harness/skins")):
            path = directory / f"{name}.css"
            if path.is_file():
                return path.read_text()
        return ""

    def reload(self) -> None:
        theme = self._theme()
        self.style = inline_style(theme)
        self._provider.load_from_string(colours_css(theme) + self._skin())
        scheme_path = self._home / SCHEME_FILE
        scheme_path.parent.mkdir(parents=True, exist_ok=True)
        scheme_path.write_text(source_scheme(theme))
        manager = GtkSource.StyleSchemeManager.get_default()
        manager.force_rescan()
        self.scheme = manager.get_scheme(SCHEME_ID)
