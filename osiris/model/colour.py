"""Colour, and whether two of them can be read against each other.

Pure arithmetic. The contrast functions are the reason this is its own module
with its own tests: a theme that derives unreadable text is a defect with a
number attached, and a number can be asserted. Before these existed, a "light"
theme on a near-black background derived black text at a contrast ratio of
1.16 and nobody noticed until it was on screen.
"""

from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

#: Relative luminance of mid grey. A background below this needs light text on
#: it, whatever the theme calls itself.
MID_LUMINANCE = 0.216

#: WCAG AAA for body text, and AA for large text and interface components.
BODY_CONTRAST = 7.0
INTERFACE_CONTRAST = 4.0


class InvalidColour(ValueError):
    pass


@dataclass(frozen=True)
class Colour:
    """An sRGB colour, written the way a theme file writes it."""

    hex: str

    def __post_init__(self) -> None:
        if not _HEX.match(self.hex):
            raise InvalidColour(f"{self.hex!r} is not #rrggbb")
        object.__setattr__(self, "hex", self.hex.lower())

    # ---- constructors ------------------------------------------------------

    @classmethod
    def from_rgb(cls, red: float, green: float, blue: float) -> Colour:
        channels = (
            round(max(0.0, min(1.0, value)) * 255) for value in (red, green, blue)
        )
        return cls("#" + "".join(f"{value:02x}" for value in channels))

    @classmethod
    def from_hls(cls, hue: float, lightness: float, saturation: float) -> Colour:
        return cls.from_rgb(
            *colorsys.hls_to_rgb(
                hue % 1.0,
                max(0.0, min(1.0, lightness)),
                max(0.0, min(1.0, saturation)),
            )
        )

    # ---- views -------------------------------------------------------------

    @property
    def rgb(self) -> tuple[float, float, float]:
        value = self.hex.lstrip("#")
        return tuple(int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]

    @property
    def hls(self) -> tuple[float, float, float]:
        red, green, blue = self.rgb
        return colorsys.rgb_to_hls(red, green, blue)

    @property
    def luminance(self) -> float:
        """Relative luminance, by the WCAG definition."""

        def channel(value: float) -> float:
            return (
                value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
            )

        red, green, blue = (channel(value) for value in self.rgb)
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue

    @property
    def is_dark(self) -> bool:
        return self.luminance < MID_LUMINANCE

    # ---- operations --------------------------------------------------------

    def mix(self, other: Colour, amount: float) -> Colour:
        """Blend towards `other` by `amount` (0-1)."""
        return Colour.from_rgb(
            *(
                mine + (theirs - mine) * amount
                for mine, theirs in zip(self.rgb, other.rgb, strict=True)
            )
        )

    def contrast(self, other: Colour) -> float:
        """The WCAG contrast ratio between two colours, 1.0 to 21.0."""
        mine, theirs = self.luminance, other.luminance
        lighter, darker = max(mine, theirs), min(mine, theirs)
        return (lighter + 0.05) / (darker + 0.05)

    def readable_against(
        self, background: Colour, minimum: float = BODY_CONTRAST
    ) -> bool:
        return self.contrast(background) >= minimum


BLACK = Colour("#000000")
WHITE = Colour("#ffffff")


def hue_distance(one: Colour, other: Colour) -> float:
    """How far apart two hues are on the circle, 0 to 0.5."""
    difference = abs(one.hls[0] - other.hls[0])
    return min(difference, 1.0 - difference)
