"""Render the Osiris logo as braille art for fastfetch.

    python3 branding/scripts/make-terminal-logo.py [cols] [rows]

Writes branding/logo.txt.

Two stages, because each tool does one thing well:

  1. ImageMagick renders branding/logo.svg and closes the gaps between its
     interior lines, producing branding/logo-simple.png. Without this the
     circuit detail inside the mark turns into static at terminal size.
  2. chafa converts that to braille. Braille packs 2x4 subpixels into one
     character cell - eight times the detail of a plain ASCII ramp and four
     times a half-block - which is what thin isometric linework needs.

Earlier attempts (brightness ramp, hand-drawing, half-blocks) all failed: the
ramp produced noise, hand-drawing lost the isometric read, and half-blocks
could not resolve the interior detail.

Needs `imagemagick` and `chafa`; both are in Arch's repositories.
"""
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SVG = os.path.join(REPO, "branding", "logo.svg")
SIMPLE = os.path.join(REPO, "branding", "logo-simple.png")
DEST = os.path.join(REPO, "branding", "logo.txt")

# Radius that closes the gaps between interior lines without melting the
# separate tiers into one blob. Larger values lose the stepped silhouette.
CLOSE_RADIUS = 8


def require(tool: str) -> None:
    if shutil.which(tool) is None:
        sys.exit(f"{tool} is required (pacman -S {tool})")


def simplify() -> None:
    require("magick")
    subprocess.run(
        ["magick", "-background", "none", "-density", "300", SVG,
         "-trim", "+repage", "-alpha", "extract",
         "-morphology", "Close", f"Disk:{CLOSE_RADIUS}",
         "-bordercolor", "black", "-border", "10", SIMPLE],
        check=True, capture_output=True)
    print(f"  wrote {SIMPLE}")


def render(cols: int, rows: int) -> str:
    require("chafa")
    return subprocess.run(
        ["chafa", "--symbols", "braille", "--fg-only",
         "--format", "symbols", "--size", f"{cols}x{rows}", SIMPLE],
        check=True, capture_output=True, text=True).stdout


def main() -> None:
    cols = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    rows = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    if not os.path.exists(SVG):
        sys.exit(f"missing {SVG}")
    simplify()
    art = "\n".join(line.rstrip() for line in render(cols, rows).splitlines())
    with open(DEST, "w") as fh:
        fh.write(art.strip("\n") + "\n")
    print(art)
    print(f"\nwrote {DEST} ({cols}x{rows})")


if __name__ == "__main__":
    main()
