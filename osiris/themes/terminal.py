"""The terminal's look, as a ghostty theme Osiris owns.

ghostty finds ``theme = osiris`` in ~/.config/ghostty/themes/, and anything the
person sets in their own config wins over it, so the engine rewrites the theme
on every switch and never touches their config.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

THEME = "osiris"
THEME_FILE = f".config/ghostty/themes/{THEME}"
CONFIG_FILE = ".config/ghostty/config"

CONFIG = f"""\
# Your ghostty settings. Osiris wrote this once and leaves it to you: anything
# set here wins over the Osiris theme, which follows your Theme.
theme = {THEME}
"""

_PALETTE = [f"regular{n}" for n in range(8)] + [f"bright{n}" for n in range(8)]


def theme_file(theme: Mapping[str, Any], *, mono: str) -> str:
    c, t = theme["colors"], theme.get("terminal", {})
    palette = "\n".join(
        f"palette = {i}={t[key]}" for i, key in enumerate(_PALETTE) if key in t
    )
    return f"""\
# Written by Osiris on every Theme switch. Change ~/{CONFIG_FILE} instead.
font-family = {mono}
font-size = 11
font-feature = calt
font-feature = liga

background = {c["background"]}
foreground = {c["foreground"]}
cursor-color = {c["accent"]}
selection-background = {c["surfaceMuted"]}
selection-foreground = {c["foreground"]}
{palette}

background-opacity = 0.92
window-padding-x = 10
window-padding-y = 10
window-decoration = auto
scrollback-limit = 10000000
confirm-close-surface = false
# A theme switch reloads every open terminal; a toast in each one is noise.
app-notifications = no-config-reload
"""
