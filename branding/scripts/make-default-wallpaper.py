#!/usr/bin/env python3
"""
Generate the Osiris default wallpaper.

Produces a vertical dark gradient with the Osiris logo centered.
Output: branding/wallpapers/osiris-default.png
"""

from pathlib import Path
from PIL import Image

WIDTH, HEIGHT = 2560, 1440
TOP_COLOR = (10, 10, 18)
BOTTOM_COLOR = (26, 20, 36)
LOGO_SCALE = 0.18
LOGO_OPACITY = 200

SCRIPT_DIR = Path(__file__).parent
BRANDING_DIR = SCRIPT_DIR.parent
LOGO_PATH = BRANDING_DIR / "logo-dark.png"
OUTPUT_DIR = BRANDING_DIR / "wallpapers"
OUTPUT_PATH = OUTPUT_DIR / "osiris-default.png"


def vertical_gradient(width: int, height: int, top: tuple, bottom: tuple) -> Image.Image:
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    for y in range(height):
        t = y / (height - 1)
        r = round(top[0] + (bottom[0] - top[0]) * t)
        g = round(top[1] + (bottom[1] - top[1]) * t)
        b = round(top[2] + (bottom[2] - top[2]) * t)
        for x in range(width):
            pixels[x, y] = (r, g, b)
    return img


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    base = vertical_gradient(WIDTH, HEIGHT, TOP_COLOR, BOTTOM_COLOR).convert("RGBA")

    logo = Image.open(LOGO_PATH).convert("RGBA")
    new_size = (int(logo.width * LOGO_SCALE), int(logo.height * LOGO_SCALE))
    logo = logo.resize(new_size, Image.Resampling.LANCZOS)

    if LOGO_OPACITY < 255:
        r, g, b, a = logo.split()
        a = a.point(lambda v: int(v * (LOGO_OPACITY / 255)))
        logo = Image.merge("RGBA", (r, g, b, a))

    pos = ((WIDTH - logo.width) // 2, (HEIGHT - logo.height) // 2)
    base.paste(logo, pos, logo)

    base.convert("RGB").save(OUTPUT_PATH, format="PNG", optimize=True)
    print(f"wrote {OUTPUT_PATH} ({WIDTH}x{HEIGHT})")


if __name__ == "__main__":
    main()
