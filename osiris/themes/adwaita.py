"""The Theme's palette as libadwaita's colours.

libadwaita applications ignore the GTK theme a Theme compiles (ADR 0006) and
draw from their own colours, which a person's ``~/.config/gtk-4.0/gtk.css`` may
override. The theme engine writes this there, so every libadwaita application,
Programs included, follows the Theme as GTK 3 applications do.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from osiris.model.colour import Colour


def _readable_on(colours: Mapping[str, str], fill: str) -> str:
    """Whichever end of the palette reads on ``fill``."""
    behind = Colour(colours[fill])
    return max(
        (colours["background"], colours["foreground"]),
        key=lambda end: Colour(end).contrast(behind),
    )


def adwaita_css(theme: Mapping[str, Any]) -> str:
    """Named colours, and the same as the CSS variables libadwaita 1.6 reads."""
    c: Mapping[str, str] = theme["colors"]
    on_accent, on_danger = _readable_on(c, "accent"), _readable_on(c, "danger")
    colours = {
        "window_bg_color": c["surface"],
        "window_fg_color": c["foreground"],
        "view_bg_color": c["background"],
        "view_fg_color": c["foreground"],
        "headerbar_bg_color": c["surface"],
        "headerbar_fg_color": c["foreground"],
        "sidebar_bg_color": c["surfaceMuted"],
        "sidebar_fg_color": c["foreground"],
        "card_bg_color": c["surfaceMuted"],
        "card_fg_color": c["foreground"],
        "popover_bg_color": c["surface"],
        "popover_fg_color": c["foreground"],
        "dialog_bg_color": c["surface"],
        "dialog_fg_color": c["foreground"],
        "accent_color": c["accent"],
        "accent_bg_color": c["accent"],
        "accent_fg_color": on_accent,
        "destructive_color": c["danger"],
        "destructive_bg_color": c["danger"],
        "destructive_fg_color": on_danger,
        "success_color": c["success"],
        "success_bg_color": c["success"],
        "success_fg_color": c["background"],
        "warning_color": c["warning"],
        "warning_bg_color": c["warning"],
        "warning_fg_color": c["background"],
        "error_color": c["danger"],
        "error_bg_color": c["danger"],
        "error_fg_color": on_danger,
    }
    named = [f"@define-color {name} {value};" for name, value in colours.items()]
    variables = [
        f"  --{name.replace('_', '-')}: {value};" for name, value in colours.items()
    ]
    return "\n".join([*named, ":root {", *variables, "}"]) + "\n"
