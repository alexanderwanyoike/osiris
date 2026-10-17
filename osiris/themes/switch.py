"""A theme switch as one dconf change.

Setting each key with its own ``gsettings set`` reached the desktop as one
change per key, and every one repainted on its own: applications restyled, then
title bars, then the panel, then icons, then the wallpaper. ``dconf load`` of a
single keyfile reaches every client as one notification carrying all the keys
(one ``Notify`` signal, measured with dbus-monitor), so they change together.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Switch:
    """What a switch sets. ``theme`` names the generated GTK, Muffin and
    Cinnamon theme; ``wallpaper`` and ``dock`` are left alone when None."""

    theme: str
    icons: str
    cursor: str
    font: str
    dark: bool
    wallpaper: str | None
    dock: str | None


def _string(text: str) -> str:
    """A GVariant string literal, which is what dconf keyfiles hold."""
    escaped = text.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def keyfile(switch: Switch, dock_path: str) -> str:
    """The switch as a keyfile for ``dconf load /``.

    ``dock_path`` is the relocatable path of Plank's dock settings.
    """
    sections: dict[str, dict[str, str]] = {
        "org/cinnamon/desktop/interface": {
            "gtk-theme": switch.theme,
            "icon-theme": switch.icons,
            "cursor-theme": switch.cursor,
            "font-name": switch.font,
        },
        "org/cinnamon/desktop/wm/preferences": {"theme": switch.theme},
        "org/cinnamon/theme": {"name": switch.theme},
        "org/gnome/desktop/interface": {
            "gtk-theme": switch.theme,
            "icon-theme": switch.icons,
            "color-scheme": "prefer-dark" if switch.dark else "prefer-light",
        },
    }
    if switch.wallpaper is not None:
        sections["org/cinnamon/desktop/background"] = {
            "picture-uri": f"file://{switch.wallpaper}",
            "picture-options": "zoom",
        }
    if switch.dock is not None:
        sections[dock_path.strip("/")] = {"theme": switch.dock}

    lines: list[str] = []
    for section, keys in sections.items():
        lines.append(f"[{section}]")
        lines.extend(f"{key}={_string(value)}" for key, value in keys.items())
        lines.append("")
    return "\n".join(lines)
