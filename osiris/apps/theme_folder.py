"""Hear of Themes added to, changed in or taken from the person's folder,
whoever does it."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib  # noqa: E402

from osiris.apps.user_css import WRITTEN  # noqa: E402


class ThemeFolder:
    #: One write is heard as a file created and then finished; heard once,
    #: after the writer is done.
    QUIET_MS = 250

    def __init__(self, folder: Path, changed: Callable[[], None]) -> None:
        self._changed = changed
        self._waiting = False
        # A directory monitor on a folder not yet made never hears what is
        # later written into it.
        folder.mkdir(parents=True, exist_ok=True)
        self._monitor = Gio.File.new_for_path(str(folder)).monitor_directory(
            Gio.FileMonitorFlags.NONE, None
        )
        self._monitor.connect("changed", self._heard)

    def _heard(
        self, _monitor: object, file: Gio.File, _other: object, event: object
    ) -> None:
        # The engine reads only these; see engine._files.
        if event not in WRITTEN or not (file.get_basename() or "").endswith(".json"):
            return
        if not self._waiting:
            self._waiting = True
            GLib.timeout_add(self.QUIET_MS, self._quiet)

    def _quiet(self) -> bool:
        self._waiting = False
        self._changed()
        return False
