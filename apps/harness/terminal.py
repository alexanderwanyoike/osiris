"""A terminal in the Canvas's terminal group (#196): VTE, the embeddable GTK 4
terminal, running the person's shell in a Program's folder, in the Theme's
terminal colours and font. VTE draws no ligatures; the desktop's terminal,
ghostty, does."""

import os
import signal
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Vte", "3.91")
from gi.repository import Gdk, GLib, Pango, Vte  # noqa: E402

from osiris.themes.terminal import palette  # noqa: E402

#: The terminal's size, as ghostty's own.
FONT_SIZE = 11


def _rgba(hex_colour: str) -> Gdk.RGBA:
    colour = Gdk.RGBA()
    colour.parse(hex_colour)
    return colour


class Terminal(Vte.Terminal):
    def __init__(self, folder: Path, theme: Mapping[str, Any]):
        super().__init__(vexpand=True, hexpand=True)
        self.add_css_class("harness-terminal")
        self.pid: int | None = None
        self.restyle(theme)
        self.spawn_async(Vte.PtyFlags.DEFAULT, str(folder), [Vte.get_user_shell()],
                         None, GLib.SpawnFlags.DEFAULT, None, None, -1, None,
                         self._spawned)

    def _spawned(self, _terminal, pid: int, error, *_data) -> None:
        if error is None:
            self.pid = pid

    def restyle(self, theme: Mapping[str, Any]) -> None:
        """Follow a Theme change, as ghostty does."""
        colours = theme["colors"]
        mono = theme.get("ui", {}).get("mono", "monospace")
        self.set_font(Pango.FontDescription.from_string(f"{mono} {FONT_SIZE}"))
        self.set_colors(_rgba(colours["foreground"]), _rgba(colours["background"]),
                        [_rgba(hex_colour) for hex_colour in palette(theme)])
        self.set_color_cursor(_rgba(colours["accent"]))

    def close(self) -> None:
        """End the shell, as closing a terminal window does."""
        if self.pid is not None:
            try:
                os.kill(self.pid, signal.SIGHUP)
            except ProcessLookupError:
                pass
