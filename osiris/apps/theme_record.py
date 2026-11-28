"""Hear which Theme the engine's record names, whoever applies it."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio  # noqa: E402

from osiris.apps.user_css import WRITTEN  # noqa: E402


class ThemeRecord:
    def __init__(self, record: Path, applied: Callable[[str], None]) -> None:
        self._record = record
        self._applied = applied
        self._monitor = Gio.File.new_for_path(str(record)).monitor_file(
            Gio.FileMonitorFlags.NONE, None
        )
        self._monitor.connect("changed", self._heard)

    def _heard(
        self, _monitor: object, _file: object, _other: object, event: object
    ) -> None:
        if event not in WRITTEN:
            return
        try:
            name = self._record.read_text().strip()
        except OSError:
            return
        if name:
            self._applied(name)
