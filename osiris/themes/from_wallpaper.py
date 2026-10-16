"""A Theme intent proposed by a picture."""

from __future__ import annotations

from PIL import Image

from osiris.themes.intent import Harmony, Mood, ThemeIntent


def intent_from(
    image: Image.Image,
    harmony: Harmony | None = None,
    mood: Mood | None = None,
    dark: bool | None = None,
) -> ThemeIntent:
    raise NotImplementedError
