"""Hear of Themes added to, changed in or taken from the person's folder,
whoever does it."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio  # noqa: E402

from osiris.apps.user_css import WRITTEN  # noqa: E402


class ThemeFolder:
    def __init__(self, folder: Path, changed: Callable[[], None]) -> None:
        self._changed = changed
        self._monitor = Gio.File.new_for_path(str(folder)).monitor_directory(
            Gio.FileMonitorFlags.NONE, None
        )
        self._monitor.connect("changed", self._heard)

    def _heard(
        self, _monitor: object, _file: object, _other: object, event: object
    ) -> None:
        if event in WRITTEN:
            self._changed()
