"""A theme switch as one dconf change."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Switch:
    theme: str
    icons: str
    cursor: str
    font: str
    dark: bool
    wallpaper: str | None
    dock: str | None


def keyfile(switch: Switch, dock_path: str) -> str:
    raise NotImplementedError
