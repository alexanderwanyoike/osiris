"""What the Harness may do with Themes.

A model reaches these through the Osiris tool server. It never writes a colour:
it names a Theme intent, and Osiris's rules derive the palette (CONTEXT.md), so
a Theme made from a sentence is as harmonious and legible as one made in
Appearance. Errors are worded for the model to read and correct itself.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any

from osiris.model.colour import Colour, InvalidColour
from osiris.themes.derive import build
from osiris.themes.intent import Harmony, Mood, ThemeIntent, seeds
from osiris.themes.library import slug
from osiris.themes.store import ThemeStore


class ThemeActionError(ValueError):
    pass


def list_themes(store: ThemeStore) -> list[dict[str, object]]:
    current = store.current()
    return [
        {
            "name": theme["name"],
            "label": theme["label"],
            "dark": theme["dark"],
            "current": theme["name"] == current,
        }
        for theme in store.themes()
    ]


def _choice[E: Enum](kind: type[E], value: str, what: str) -> E:
    try:
        return kind(value)
    except ValueError as error:
        offered = ", ".join(member.value for member in kind)
        raise ThemeActionError(
            f"{value!r} is not a {what}; choose one of {offered}"
        ) from error


def create_theme(
    store: ThemeStore,
    *,
    label: str,
    seed: str,
    harmony: str,
    mood: str,
    dark: bool,
) -> str:
    """Make and keep a User theme from a Theme intent. Returns its name."""
    try:
        colour = Colour(seed)
    except InvalidColour as error:
        raise ThemeActionError(
            f"{seed!r} is not a colour; give it as #rrggbb"
        ) from error
    intent = ThemeIntent(
        seed=colour,
        harmony=_choice(Harmony, harmony, "harmony"),
        mood=_choice(Mood, mood, "mood"),
        dark=dark,
    )
    name = slug(label)
    if any(theme["name"] == name for theme in store.themes()):
        raise ThemeActionError(
            f"There is already a theme called {label}; choose another label"
        )
    store.save(build(name, label, seeds(intent)))
    return name


def find(store: ThemeStore, name: str) -> Mapping[str, Any]:
    for theme in store.themes():
        if theme["name"] == name:
            return theme
    raise ThemeActionError(f"There is no theme called {name}")


def apply_theme(store: ThemeStore, name: str) -> str | None:
    """Apply a Theme. Returns the one it replaced, which is what Undo applies."""
    find(store, name)
    previous = store.current()
    store.apply(name)
    return previous


def delete_theme(store: ThemeStore, name: str) -> None:
    """Delete a theme, which is how making one is undone."""
    theme = find(store, name)
    if store.current() == name:
        raise ThemeActionError(
            f"{theme['label']} is applied; apply another theme first"
        )
    store.delete(name)
