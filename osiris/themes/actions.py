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
_CHARGED = "It may still have been charged, so ask the person before trying again."


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
    theme = _document(store, label, seed, harmony, mood, dark)
    store.save(theme)
    return str(theme["name"])


def make_theme_pair(
    store: ThemeStore, *, label: str, seed: str, harmony: str, mood: str
) -> tuple[str, str]:
    """Make a light Theme and a dark one from one idea, each naming the other.
    Returns their names, light first."""
    light = _document(store, label, seed, harmony, mood, False)
    dark = _document(store, f"{label} Night", seed, harmony, mood, True)
    store.save({**light, "pair": dark["name"]})
    store.save({**dark, "pair": light["name"]})
    return str(light["name"]), str(dark["name"])


def make_other_half(store: ThemeStore, name: str) -> str:
    """Make the light or dark Theme a Theme made alone lacks, from its accent,
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
    )
    store.save({**theme, "pair": other["name"]})
    store.save({**other, "pair": name})
    return str(other["name"])


def _document(
    store: ThemeStore, label: str, seed: str, harmony: str, mood: str, dark: bool
) -> dict[str, object]:
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
    return build(name, label, seeds(intent))


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
        raise ThemeActionError(f"The picture could not be read. {_CHARGED}") from error
    try:
        kept = keep(name, png)
    except OSError as error:
        raise ThemeActionError(f"The picture could not be saved. {_CHARGED}") from error
    store.save(
        {
            **build(name, label, seeds(intent)),
            "intent": {
                "seed": intent.seed.hex,
                "harmony": intent.harmony.value,
                "mood": intent.mood.value,
            },
            "wallpaper": str(kept),
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


#: What a desktop background can be drawn from.
PICTURE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")


def wear_picture(
    store: ThemeStore,
    name: str,
    picture: Path,
    keep: Callable[[str, Path], Path],
) -> str | None:
    """Make ``picture`` the Theme's wallpaper, kept by ``keep`` under the
    Theme's name. Returns the wallpaper it replaced."""
    if picture.suffix.lower() not in PICTURE_SUFFIXES:
        raise ThemeActionError(
            f"{picture.name} is not a picture; give a PNG, JPEG or WebP file"
        )
    theme = find(store, name)
    store.save({**theme, "wallpaper": str(keep(name, picture))})
    previous = theme.get("wallpaper")
    return str(previous) if previous else None


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
