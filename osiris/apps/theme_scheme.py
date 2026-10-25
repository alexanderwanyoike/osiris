"""Keep a libadwaita app in the active Theme's light or dark, whoever changes it.

libadwaita takes light or dark from the XDG settings portal, which Cinnamon
does not serve, so each Osiris app follows the Theme engine's record instead.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import gi

gi.require_version("Adw", "1")
from gi.repository import Adw, Gio  # noqa: E402


class ThemeScheme:
    def __init__(self, record: Path, load: Callable[[str], Mapping[str, Any]]) -> None:
        self._record = record
        self._load = load
        self._monitor = Gio.File.new_for_path(str(record)).monitor_file(
            Gio.FileMonitorFlags.NONE, None
        )
        self._monitor.connect("changed", lambda *_args: self.follow())
        self.follow()

    def follow(self) -> None:
        try:
            dark = bool(self._load(self._record.read_text().strip()).get("dark", True))
        except OSError, KeyError, ValueError:
            dark = True
        Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.FORCE_DARK if dark else Adw.ColorScheme.FORCE_LIGHT
        )
