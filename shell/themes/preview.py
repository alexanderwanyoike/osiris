"""Render a desktop preview thumbnail for each theme.

    python3 shell/themes/preview.py            # all themes
    python3 shell/themes/preview.py nord       # one

Writes shell/themes/previews/<name>.png.

A miniature of the actual desktop - wallpaper gradient, top panel, a focused
window with the accent border, and the dock - so the picker shows what a theme
looks like rather than a row of colour swatches.

Uses Pillow, which is already a dependency of the desktop; no ImageMagick, so
this also runs on the installed system.
"""
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wallpaper as wallpaper_module  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "previews")

# Bumped whenever this module or wallpaper.py changes what it draws. Cached
# user assets record it, so a change to the renderer refreshes them; without
# it a theme keeps the artwork of whatever generator first saw it.
RENDERER_VERSION = 2

W, H = 400, 250
PANEL_H = 16
RADIUS = 7


def rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def mix(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def wallpaper(image: Image.Image, theme: dict) -> None:
    """Paste the theme's actual wallpaper in behind the miniature.

    Rendered at preview size rather than downscaled from the full 1440p file:
    the file may not exist yet for a theme the user has just written, and the
    generator is parameterised by size anyway. The card therefore shows the
    background the user will actually get - an earlier version drew its own
    gradient here and the cards quietly stopped matching the desktop.
    """
    image.paste(wallpaper_module.compose(theme, (W, H)), (0, 0))


def panel(draw: ImageDraw.ImageDraw, c: dict) -> None:
    draw.rectangle([0, 0, W, PANEL_H], fill=rgb(c["surface"]))
    draw.line([(0, PANEL_H), (W, PANEL_H)], fill=rgb(c["border"]))
    # menu dot, then indicators on the right
    draw.ellipse([7, 5, 15, 13], fill=rgb(c["foregroundMuted"]))
    x = W - 14
    for shade in ("foregroundMuted", "foregroundMuted", "foreground"):
        draw.rectangle([x, 6, x + 7, 11], fill=rgb(c[shade]))
        x -= 12


def window(draw: ImageDraw.ImageDraw, c: dict) -> None:
    x0, y0, x1, y1 = 54, 50, W - 54, H - 62
    draw.rounded_rectangle([x0 + 3, y0 + 4, x1 + 3, y1 + 4],
                           RADIUS, fill=mix(rgb(c["background"]), (0, 0, 0), 0.35))
    draw.rounded_rectangle([x0, y0, x1, y1], RADIUS,
                           fill=rgb(c["background"]),
                           outline=rgb(c["borderActive"]), width=2)
    # title bar
    draw.rounded_rectangle([x0, y0, x1, y0 + 18], RADIUS, fill=rgb(c["surface"]))
    draw.rectangle([x0, y0 + 12, x1, y0 + 18], fill=rgb(c["surface"]))
    for i, key in enumerate(("foregroundMuted", "foregroundMuted", "danger")):
        draw.ellipse([x1 - 13 - i * 11, y0 + 6, x1 - 7 - i * 11, y0 + 12],
                     fill=rgb(c[key]))
    # content: a prompt line then muted text lines
    y = y0 + 30
    draw.rectangle([x0 + 12, y, x0 + 20, y + 4], fill=rgb(c["accent"]))
    draw.rectangle([x0 + 26, y, x0 + 96, y + 4], fill=rgb(c["foreground"]))
    for width, key in ((120, "foregroundMuted"), (86, "success"),
                       (104, "foregroundMuted"), (64, "warning")):
        y += 13
        draw.rectangle([x0 + 12, y, x0 + 12 + width, y + 4], fill=rgb(c[key]))


def dock(draw: ImageDraw.ImageDraw, c: dict) -> None:
    w, h = 150, 26
    x0, y0 = (W - w) // 2, H - h - 8
    draw.rounded_rectangle([x0, y0, x0 + w, y0 + h], 9,
                           fill=rgb(c["surface"]), outline=rgb(c["border"]))
    for i, key in enumerate(("accent", "foregroundMuted", "foregroundMuted",
                             "foregroundMuted", "accentMuted")):
        cx = x0 + 19 + i * 28
        draw.rounded_rectangle([cx - 8, y0 + 6, cx + 8, y0 + 20], 4,
                               fill=rgb(c[key]))


def render_theme(theme: dict, dest: str) -> str:
    """Render a preview for an already-loaded theme to an explicit path."""
    c = theme["colors"]
    image = Image.new("RGB", (W, H))
    wallpaper(image, theme)
    draw = ImageDraw.Draw(image)
    panel(draw, c)
    window(draw, c)
    dock(draw, c)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    image.save(dest)
    return dest


def render_wallpaper(theme: dict, dest: str,
                     size: tuple[int, int] = (2560, 1440)) -> str:
    """Full-size wallpaper for a theme that has none on disk.

    Thin wrapper so engine.ensure_assets has a single place to call for both
    assets; the generator itself lives in wallpaper.py.
    """
    return wallpaper_module.render(theme, dest, size)


def render(path: str) -> str:
    with open(path) as fh:
        theme = json.load(fh)
    return render_theme(theme, os.path.join(OUT, f"{theme['name']}.png"))


def main() -> None:
    names = sys.argv[1:]
    paths = ([os.path.join(HERE, f"{n}.json") for n in names] if names else
             sorted(os.path.join(HERE, f) for f in os.listdir(HERE)
                    if f.endswith(".json")))
    for path in paths:
        if not os.path.exists(path):
            sys.exit(f"no such theme: {path}")
        print(f"  {render(path)}")


if __name__ == "__main__":
    main()
