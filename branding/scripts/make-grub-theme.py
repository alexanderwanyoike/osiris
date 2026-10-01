"""Generate the GRUB boot menu theme from a palette.

    python3 branding/scripts/make-grub-theme.py

Writes branding/grub/: the backdrop, the mark, and the 9-slice pixmaps for the
selection highlight. The theme.txt beside them is hand-written and references
these by name.

The bootloader runs before any user session exists, so it cannot follow the
user's chosen theme - it is generated from `osiris-obsidian` and stays branded,
the same decision as the boot splash and the greeter.

9-slice is how GRUB scales a box: it draws the four corners at their natural
size, tiles the four edges along each side, and tiles the centre to fill. A set
is nine files named `<prefix>_<position>.png` with positions c, n, s, e, w, nw,
ne, sw and se. Get one wrong and GRUB silently draws nothing.
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, "branding", "grub")
sys.path.insert(0, os.path.join(REPO, "shell", "themes"))

import wallpaper  # noqa: E402

RADIUS = 8          # corner size, and therefore the 9-slice corner tile size
LOGO_HEIGHT = 220
SIZE = (1920, 1080)


def rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def nine_slice(prefix: str, fill: tuple[int, int, int, int]) -> None:
    """Write a nine-piece set for a rounded box of one colour."""
    box = Image.new("RGBA", (RADIUS * 2 + 2, RADIUS * 2 + 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(box)
    draw.rounded_rectangle([0, 0, box.width - 1, box.height - 1],
                           RADIUS, fill=fill)
    r, far = RADIUS, RADIUS + 2
    pieces = {
        "nw": box.crop((0, 0, r, r)),
        "ne": box.crop((far, 0, box.width, r)),
        "sw": box.crop((0, far, r, box.height)),
        "se": box.crop((far, far, box.width, box.height)),
        "n": box.crop((r, 0, r + 1, r)),
        "s": box.crop((r, far, r + 1, box.height)),
        "w": box.crop((0, r, r, r + 1)),
        "e": box.crop((far, r, box.width, r + 1)),
        "c": box.crop((r, r, r + 1, r + 1)),
    }
    for position, image in pieces.items():
        image.save(os.path.join(OUT, f"{prefix}_{position}.png"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", default="osiris-obsidian")
    args = parser.parse_args()

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(REPO, "shell", "themes", f"{args.theme}.json")
    with open(path) as fh:
        theme = json.load(fh)
    colors = theme["colors"]

    wallpaper.boot_background(theme, SIZE).save(
        os.path.join(OUT, "background.png"))
    print(f"  background.png  {SIZE[0]}x{SIZE[1]}")

    # The mark, trimmed to its ink and kept as RGBA so GRUB composites it over
    # the backdrop rather than over a black rectangle.
    mask_path = os.path.join(REPO, "branding", "logo-mask.png")
    mask = Image.open(mask_path).convert("L")
    scale = LOGO_HEIGHT / mask.height
    mask = mask.resize((max(1, round(mask.width * scale)), LOGO_HEIGHT),
                       Image.LANCZOS)
    ink = Image.new("RGBA", mask.size, (*rgb(colors["foreground"]), 0))
    ink.putalpha(mask)
    ink.save(os.path.join(OUT, "logo.png"))
    print(f"  logo.png        {ink.width}x{ink.height}")

    nine_slice("select", (*rgb(colors["accent"]), 56))
    print(f"  select_*.png    9 pieces, accent {colors['accent']}")


if __name__ == "__main__":
    main()
