"""What the Harness may do with Themes.

A model reaches these through the Osiris tool server. It never writes a colour:
it names a Theme intent, and Osiris's rules derive the palette (CONTEXT.md), so
a Theme made from a sentence is as harmonious and legible as one made in
Appearance. Errors are worded for the model to read and correct itself.
"""

from __future__ import annotations

import io
from collections.abc import Callable, Mapping
from enum import Enum
from pathlib import Path
from typing import Any

from PIL import Image

from osiris.model.colour import Colour, InvalidColour
from osiris.model.names import slug
from osiris.themes.derive import build
from osiris.themes.from_wallpaper import intent_from
from osiris.themes.intent import Harmony, Mood, ThemeIntent, seeds
from osiris.themes.store import ThemeStore

# A Theme's name becomes file and folder names, with prefixes and suffixes.
_LONGEST_NAME = 64


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
    name = unused_name(store, label)
    store.save(build(name, label, seeds(intent)))
    return name


def unused_name(store: ThemeStore, label: str) -> str:
    """The name ``label`` gives a new Theme; a label in use is refused."""
    name = slug(label)
    if len(name) > _LONGEST_NAME:
        raise ThemeActionError(
            f"That label is too long; keep it to {_LONGEST_NAME} characters or fewer"
        )
    if any(theme["name"] == name for theme in store.themes()):
        raise ThemeActionError(
            f"There is already a theme called {label}; choose another label"
        )
    return name


def create_picture_theme(
    store: ThemeStore,
    *,
    label: str,
    picture: bytes,
    keep: Callable[[str, bytes], Path],
) -> str:
    """Make a User theme wearing ``picture``, its colours proposed by it.

    ``keep`` stores the picture, as a PNG, under the Theme's name and says where.
    """
    name = unused_name(store, label)
    try:
        image = Image.open(io.BytesIO(picture))
        intent = intent_from(image)
        png = picture if image.format == "PNG" else _as_png(image)
    except (OSError, ValueError) as error:
        raise ThemeActionError(
            "The picture could not be read. It may still have been charged, so ask "
            "the person before trying again."
        ) from error
    store.save(
        {
            **build(name, label, seeds(intent)),
            "intent": {
                "seed": intent.seed.hex,
                "harmony": intent.harmony.value,
                "mood": intent.mood.value,
            },
            "wallpaper": str(keep(name, png)),
        }
    )
    return name


def _as_png(image: Image.Image) -> bytes:
    data = io.BytesIO()
    image.convert("RGB").save(data, "PNG")
    return data.getvalue()


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
