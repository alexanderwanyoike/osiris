"""Colour, and whether two of them can be read against each other.

Pure arithmetic. The contrast functions are the reason this is its own module
with its own tests: a theme that derives unreadable text is a defect with a
number attached, and a number can be asserted. Before these existed, a "light"
theme on a near-black background derived black text at a contrast ratio of
1.16 and nobody noticed until it was on screen.
"""

from __future__ import annotations

import colorsys
import math
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


# OKLab, Björn Ottosson, https://bottosson.github.io/posts/oklab/ - a space in
# which equal steps look equal, which HLS is not: a yellow and a blue at the same
# HLS lightness look nothing alike, so colours matched there clash.


def _to_linear(channel: float) -> float:
    if channel <= 0.04045:
        return channel / 12.92
    return float(((channel + 0.055) / 1.055) ** 2.4)


def _from_linear(channel: float) -> float:
    if channel <= 0.0031308:
        return 12.92 * channel
    return float(1.055 * channel ** (1 / 2.4) - 0.055)


def _oklab_to_linear_rgb(
    lightness: float, a: float, b: float
) -> tuple[float, float, float]:
    l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * b
    long, medium, short = l_**3, m_**3, s_**3
    return (
        +4.0767416621 * long - 3.3077115913 * medium + 0.2309699292 * short,
        -1.2684380046 * long + 2.6097574011 * medium - 0.3413193965 * short,
        -0.0041960863 * long - 0.7034186147 * medium + 1.7076147010 * short,
    )


def _in_gamut(rgb: tuple[float, float, float]) -> bool:
    return all(-1e-6 <= channel <= 1 + 1e-6 for channel in rgb)


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

    @classmethod
    def from_oklch(cls, lightness: float, chroma: float, hue: float) -> Colour:
        """The colour at OKLCH (lightness 0-1, chroma, hue in degrees).

        Where that is outside sRGB, chroma is reduced until it fits, keeping
        the lightness and hue - which is what the eye judges first.
        """
        lightness = max(0.0, min(1.0, lightness))
        angle = math.radians(hue)

        def at(c: float) -> tuple[float, float, float]:
            return _oklab_to_linear_rgb(
                lightness, c * math.cos(angle), c * math.sin(angle)
            )

        rgb = at(chroma)
        if not _in_gamut(rgb):
            low, high = 0.0, chroma
            for _ in range(24):
                middle = (low + high) / 2
                if _in_gamut(at(middle)):
                    low = middle
                else:
                    high = middle
            rgb = at(low)
        return cls.from_rgb(*(_from_linear(max(0.0, c)) for c in rgb))

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
    def oklch(self) -> tuple[float, float, float]:
        """(lightness 0-1, chroma, hue in degrees 0-360)."""
        red, green, blue = (_to_linear(channel) for channel in self.rgb)
        long = 0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue
        medium = 0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue
        short = 0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue
        l_, m_, s_ = (
            math.copysign(abs(v) ** (1 / 3), v) for v in (long, medium, short)
        )
        lightness = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
        a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
        b = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
        return (
            lightness,
            math.hypot(a, b),
            math.degrees(math.atan2(b, a)) % 360.0,
        )

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
