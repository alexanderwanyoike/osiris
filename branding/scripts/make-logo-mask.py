"""Render logo.svg to the alpha mask the wallpaper generator composites.

    python3 branding/scripts/make-logo-mask.py

Writes branding/logo-mask.png: 8-bit greyscale, white where the mark is ink,
cropped to the ink's bounding box so callers control the size directly rather
than guessing at the SVG's generous margin.

Run on a development machine - rsvg-convert is not installed on the target.
The mask is checked in and shipped, so the generator needs no SVG stack.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SOURCE = os.path.join(REPO, "branding", "logo.svg")
DEST = os.path.join(REPO, "branding", "logo-mask.png")

# Height of the rendered canvas, not of the mark: the mark occupies about 40%
# of the SVG's square viewBox, so this yields an ink box around 2000px tall.
# It is composited at roughly 500px on a 1440p wallpaper, leaving plenty of
# margin for downscaling without aliasing the line art.
HEIGHT = 4800


def main() -> None:
    if not os.path.exists(SOURCE):
        sys.exit(f"missing {SOURCE}")

    raw = os.path.join(os.path.dirname(DEST), ".logo-mask-raw.png")
    try:
        subprocess.run(["rsvg-convert", "-h", str(HEIGHT), SOURCE, "-o", raw],
                       check=True)
        # The SVG fills black on transparent, so the alpha channel is the mask.
        # -trim crops the margin; +repage discards the offset it records.
        subprocess.run(["magick", raw, "-alpha", "extract", "-trim", "+repage",
                        "-colorspace", "Gray", "-depth", "8", DEST], check=True)
    except FileNotFoundError as error:
        sys.exit(f"{error}: this script needs rsvg-convert and ImageMagick")
    except subprocess.CalledProcessError as error:
        sys.exit(f"render failed: {error}")
    finally:
        if os.path.exists(raw):
            os.remove(raw)

    size = subprocess.run(["magick", "identify", "-format", "%wx%h", DEST],
                          capture_output=True, text=True, check=True).stdout
    print(f"{DEST} ({size})")


if __name__ == "__main__":
    main()
