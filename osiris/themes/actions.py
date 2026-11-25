"""What the Harness may do with Themes.

A model reaches these through the Osiris tool server. It never writes a colour:
it names a Theme intent, and Osiris's rules derive the palette (CONTEXT.md), so
a Theme made from a sentence is as harmonious and legible as one made in
Appearance. Errors are worded for the model to read and correct itself.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any

from osiris.model.colour import Colour, InvalidColour
from osiris.model.names import slug
from osiris.themes.derive import build
from osiris.themes.intent import Harmony, Mood, ThemeIntent, seeds
from osiris.themes.store import ThemeStore


class ThemeActionError(ValueError):
    pass


#: Every Theme has its accent; a look known for more colours names up to two more.
MOST_EXTRA_ACCENTS = 2


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
    accents: Sequence[str] = (),
) -> str:
    """Make and keep a User theme from a Theme intent and the extra accents its
    look has, if any. Returns its name."""
    theme = _document(store, label, seed, harmony, mood, dark, accents)
    store.save(theme)
    return str(theme["name"])


def make_theme_pair(
    store: ThemeStore,
    *,
    label: str,
    seed: str,
    harmony: str,
    mood: str,
    accents: Sequence[str] = (),
) -> tuple[str, str]:
    """Make a light Theme and a dark one from one idea, each naming the other.
    Returns their names, light first."""
    light = _document(store, label, seed, harmony, mood, False, accents)
    dark = _document(store, f"{label} Night", seed, harmony, mood, True, accents)
    store.save({**light, "pair": dark["name"]})
    store.save({**dark, "pair": light["name"]})
    return str(light["name"]), str(dark["name"])


def make_other_half(store: ThemeStore, name: str) -> str:
    """Make the light or dark Theme a Theme made alone lacks, from its accents,
    and pair the two. Returns the new one's name."""
    theme = find(store, name)
    if theme.get("pair"):
        raise ThemeActionError(f"{theme['label']} already has its other half")
    dark = not theme["dark"]
    other = _document(
        store,
        f"{theme['label']} {'Night' if dark else 'Day'}",
        theme["colors"]["accent"],
        "analogous",
        "balanced",
        dark,
        theme.get("accents", ()),
    )
    store.save({**theme, "pair": other["name"]})
    store.save({**other, "pair": name})
    return str(other["name"])


def _document(
    store: ThemeStore,
    label: str,
    seed: str,
    harmony: str,
    mood: str,
    dark: bool,
    accents: Sequence[str],
) -> dict[str, object]:
    colour = _colour(seed)
    if len(accents) > MOST_EXTRA_ACCENTS:
        raise ThemeActionError("A theme names at most two extra accents")
    extra = [_colour(accent) for accent in accents]
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
    return build(name, label, seeds(intent), accents=extra)


def _colour(text: str) -> Colour:
    try:
        return Colour(text)
    except InvalidColour as error:
        raise ThemeActionError(
            f"{text!r} is not a colour; give it as #rrggbb"
        ) from error


def find(store: ThemeStore, name: str) -> Mapping[str, Any]:
    for theme in store.themes():
        if theme["name"] == name:
            return theme
    raise ThemeActionError(f"There is no theme called {name}")


def apply_theme(store: ThemeStore, name: str) -> str | None:
    """Apply a Theme. Returns the one it replaced."""
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


def use_wallpaper(store: ThemeStore, wallpaper: str, label: str) -> tuple[str, str]:
    """Apply a copy of the Theme in use that wears ``wallpaper``.

    Returns the copy's name and the Theme it replaced, for the log.
    """
    previous = store.current()
    if previous is None:
        raise ThemeActionError("Apply a theme first; a wallpaper belongs to a theme")
    theme = find(store, previous)
    copy_label = f"{theme['label']} {label}"
    name = slug(copy_label)
    if any(other["name"] == name for other in store.themes()):
        raise ThemeActionError(
            f"There is already a theme called {copy_label}; choose another label"
        )
    store.save(
        {**theme, "name": name, "label": copy_label, "wallpaper_style": wallpaper}
    )
    store.apply(name)
    return name, previous
