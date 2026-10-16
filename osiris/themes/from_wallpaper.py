"""A Theme intent proposed by a picture.

Creating a theme from a wallpaper derives its colours from it (CONTEXT.md). The
picture only proposes an intent; osiris.themes.intent makes the colours, by the
same rules as every other theme, so a photograph cannot produce an illegible or
clashing palette.
"""

from __future__ import annotations

from PIL import Image

from osiris.model.colour import Colour
from osiris.themes.intent import Harmony, Mood, ThemeIntent

#: The picture is reduced to this many colours, at this size, before reading.
#: Enough to keep a subject apart from its ground, few enough to be quick.
COLOURS = 12
SAMPLE = (96, 96)

#: A colour covering less of the picture than this is a speck, not a subject.
MIN_SHARE = 0.02

#: Below this average OKLCH lightness the picture reads as dark.
DARK_BELOW = 0.6

#: Average OKLCH chroma bounds between a muted, a balanced and a vivid picture.
MUTED_BELOW = 0.04
VIVID_ABOVE = 0.12


def _colours(image: Image.Image) -> list[tuple[float, Colour]]:
    """The picture's main colours, each with the share of it they cover."""
    sample = image.convert("RGB")
    sample.thumbnail(SAMPLE)
    reduced = sample.quantize(colors=COLOURS, method=Image.Quantize.MEDIANCUT)
    palette = reduced.getpalette() or []
    counts = reduced.getcolors() or []
    total = sum(count for count, _ in counts)
    colours = []
    for count, index in counts:
        # A palette image counts palette indices, though Pillow types them
        # as any pixel value.
        assert isinstance(index, int)
        red, green, blue = palette[index * 3 : index * 3 + 3]
        colours.append(
            (count / total, Colour.from_rgb(red / 255, green / 255, blue / 255))
        )
    return colours


def _subject(colours: list[tuple[float, Colour]]) -> Colour:
    """The most characterful colour: colourfulness, weighted by presence.

    The square root lets a small vivid subject - a red car - outweigh a large
    grey ground, while a speck below MIN_SHARE never counts.
    """
    candidates = [(share, colour) for share, colour in colours if share >= MIN_SHARE]
    _, colour = max(
        candidates or colours,
        key=lambda pair: pair[0] ** 0.5 * pair[1].oklch[1],
    )
    if colour.oklch[1] == 0.0:
        _, colour = max(colours, key=lambda pair: pair[0])
    return colour


def intent_from(
    image: Image.Image,
    harmony: Harmony | None = None,
    mood: Mood | None = None,
    dark: bool | None = None,
) -> ThemeIntent:
    """What the picture proposes; any choice given here wins over it."""
    colours = _colours(image)
    lightness = sum(share * colour.oklch[0] for share, colour in colours)
    chroma = sum(share * colour.oklch[1] for share, colour in colours)

    if mood is None:
        if chroma < MUTED_BELOW:
            mood = Mood.MUTED
        elif chroma > VIVID_ABOVE:
            mood = Mood.VIVID
        else:
            mood = Mood.BALANCED

    return ThemeIntent(
        seed=_subject(colours),
        # Analogous keeps the theme in the picture's own family of colours.
        harmony=harmony or Harmony.ANALOGOUS,
        mood=mood,
        dark=lightness < DARK_BELOW if dark is None else dark,
    )
