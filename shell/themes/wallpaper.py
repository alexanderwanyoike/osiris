"""Generate a wallpaper from a theme palette.

    python3 shell/themes/wallpaper.py                 # every shipped theme
    python3 shell/themes/wallpaper.py nord            # one
    python3 shell/themes/wallpaper.py nord --style arcs --show-styles

Output goes to branding/wallpapers/generated/<theme>.png.

A theme gives us two or three colours. The job is to turn those into a
background that looks deliberate rather than defaulted, without any artwork to
commission and without competing with window content.

Three rules drive everything here:

**Two or three tones, no more.** The palette's background and secondary carry
the shapes; the accent appears only as line work. A wallpaper that uses the
whole palette stops reading as a background.

**The centre stays quiet.** Every style is attenuated by a radial mask so the
pattern flattens towards the middle, leaving a calm field for the Osiris mark
and for desktop icons. Without this the mark competes with the texture and both
lose - which is why phyllotaxis and similar centre-seeking algorithms are not
used here.

**Low contrast between fills.** The shapes are separated by a few percent of
lightness, not by colour. What gives the image its structure is the accent line
work on the boundaries, which is one or two pixels wide. This is the difference
between a wallpaper and a poster.

The styles are seeded from the theme name, so a theme's wallpaper is stable
across regeneration, and two themes never get the same composition.

Needs numpy and Pillow, both of which are installed on the target, so this also
runs for user-authored themes on a live system.
"""
import argparse
import json
import os
import sys
import zlib

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, "branding", "wallpapers", "generated")

WIDTH, HEIGHT = 2560, 1440

# Where the logo mask may live: development checkout first, then the installed
# location. branding/scripts/make-logo-mask.py produces it.
MASK_PATHS = (
    os.path.join(REPO, "branding", "logo-mask.png"),
    "/usr/share/osiris/logo-mask.png",
)

STYLES = ("contour", "arcs", "strata", "aurora", "dots", "cells", "bubbles",
          "ridges", "facets")
# What a theme naming no style falls back to, chosen by hashing its name. Fixed
# at the original three: hashing over STYLES would move every such theme to a
# different wallpaper whenever a style is added.
FALLBACK_STYLES = ("contour", "arcs", "strata")

LOGO_HEIGHT = 0.36       # of the image height
LOGO_ALPHA = 0.30        # a watermark, not a sticker
QUIET_RADIUS = 0.70      # of the image height; pattern fades inside this


# --------------------------------------------------------------------------- #
# colour

def to_rgb(value: str) -> np.ndarray:
    v = value.lstrip("#")
    return np.array([int(v[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def tones(theme: dict) -> dict:
    """The two or three colours the wallpaper is allowed to use.

    Derived from the palette rather than taken from it directly: window
    surfaces and the desktop behind them should not be the same colour, or the
    desktop reads as an unfilled window.
    """
    c = theme["colors"]
    dark = theme.get("dark", True)
    background = to_rgb(c["background"])
    accent = to_rgb(c["accent"])

    if dark:
        base = background * 0.62 + accent * 0.05
    else:
        # Only a slight lift. Taking a light background much further towards
        # white leaves nothing for the shapes to sit against, and the whole
        # image washes out to paper.
        base = background + (1.0 - background) * 0.12

    secondary = c.get("accentSecondary")
    if secondary:
        shape = to_rgb(secondary)
    else:
        # No secondary declared: step the base towards the accent far enough to
        # be a distinct tone, not far enough to become a second accent.
        shape = base + (accent - base) * (0.30 if dark else 0.34)

    return {"base": np.clip(base, 0, 1),
            "shape": np.clip(shape, 0, 1),
            "line": accent,
            "ink": to_rgb(c["foreground"]),
            # Line work has to be pushed harder on a light ground: the same
            # alpha that reads as a crisp hairline on a dark field disappears
            # into paper.
            "line_alpha": 0.55 if dark else 0.80,
            "dark": dark}


# --------------------------------------------------------------------------- #
# fields

def _smooth(lattice: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Upsample a small random lattice to full size with smooth interpolation.

    Pillow's bicubic resampling is the interpolation step of classic value
    noise, and it is implemented in C, which matters at 2560x1440.

    Resampled in Pillow's 32-bit float mode, not 8-bit. Quantising to bytes
    first costs nothing visually in the field itself, but iso-contours taken
    from it land on the quantisation steps, and wherever the field is nearly
    flat those steps scatter into speckle. Floats keep the contours smooth.
    """
    image = Image.fromarray(np.ascontiguousarray(lattice, dtype=np.float32),
                            mode="F")
    resized = image.resize((shape[1], shape[0]), Image.BICUBIC)
    return np.asarray(resized, dtype=np.float32)


def fbm(shape: tuple[int, int], rng: np.random.Generator,
        cells: int = 4, octaves: int = 5, gain: float = 0.5) -> np.ndarray:
    """Fractional Brownian motion: octaves of value noise, each finer and fainter.

    Normalised to [0, 1] afterwards so downstream thresholds are meaningful
    whatever the octave count.
    """
    total = np.zeros(shape, dtype=np.float32)
    amplitude, size = 1.0, cells
    for _ in range(octaves):
        total += amplitude * _smooth(rng.random((size, max(2, size // 2))), shape)
        amplitude *= gain
        size *= 2
    total -= total.min()
    return total / max(total.max(), 1e-6)


def quiet_mask(shape: tuple[int, int]) -> np.ndarray:
    """1 at the edges, 0 in the middle: how much pattern a pixel may carry.

    Smoothstep rather than a linear ramp - a linear falloff leaves a visible
    circular seam where the gradient changes.
    """
    height, width = shape
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    radius = np.hypot((x - width / 2) / height, (y - height / 2) / height)
    # Cubed rather than a plain smoothstep: the falloff has to be wide and very
    # gradual, or the pattern dissolving into the centre reads as a smudge
    # behind the mark instead of as lighting.
    t = np.clip(radius / QUIET_RADIUS, 0, 1)
    return (t * t * (3 - 2 * t)) ** 1.6


def _edges(index: np.ndarray) -> np.ndarray:
    """Boundaries between integer regions, as a 0/1 mask."""
    out = np.zeros(index.shape, dtype=np.float32)
    out[:, 1:] += index[:, 1:] != index[:, :-1]
    out[1:, :] += index[1:, :] != index[:-1, :]
    return np.clip(out, 0, 1)


# --------------------------------------------------------------------------- #
# styles
#
# Each returns (fill, line): fill is a 0-1 field selecting between base and
# shape, line is a 0-1 field of accent line work. Both are pre-attenuated by
# the quiet mask by the caller.

def contour(shape, rng, bands: int = 11):
    """Topographic iso-bands through a noise field.

    The most forgiving of the three: any field produces bands that nest, so
    there is no seed that composes badly.
    """
    field = fbm(shape, rng, cells=3, octaves=5)
    index = np.floor(field * bands)
    return index / (bands - 1), _edges(index)


def arcs(shape, rng, grid: int = 9):
    """Truchet tiling: quarter arcs joining the midpoints of each cell's edges.

    Each cell takes one of two orientations, and neighbouring arcs meet at cell
    edges whichever way they fall, so the curves always connect into continuous
    paths. That property is what makes the tiling reliable rather than lucky.
    """
    height, width = shape
    size = height / grid
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    cx, cy = np.floor(x / size), np.floor(y / size)
    fx, fy = (x / size) % 1.0, (y / size) % 1.0

    flip = rng.random((int(np.ceil(width / size)) + 1, grid + 1)) < 0.5
    flipped = flip[cx.astype(int), cy.astype(int)]
    # Two arcs per cell, centred on opposite corners; flipping swaps the pair.
    ax, ay = np.where(flipped, fx, 1 - fx), fy
    first = np.hypot(ax, ay)
    second = np.hypot(1 - ax, 1 - ay)

    # Half a cell is the radius at which arcs meet the edge midpoints.
    line = np.zeros(shape, dtype=np.float32)
    weight = max(1.5, size * 0.026) / size
    for distance in (first, second):
        line = np.maximum(line, np.clip(
            1 - np.abs(distance - 0.5) / weight, 0, 1))

    # No fill underneath. Tinting alternate cells in the second tone was tried
    # and produced camouflage: blobs at the cell scale that fight the curves.
    # The tiling carries the image on its own, so the second tone is spent on
    # the arcs instead - a third of them, picked per cell.
    quiet = rng.random((int(np.ceil(width / size)) + 1, grid + 1)) < 0.34
    return line * quiet[cx.astype(int), cy.astype(int)], line


def strata(shape, rng, layers: int = 13):
    """Horizontal bands warped by a slow field: sedimentary rock, essentially.

    The warp amplitude is small relative to the band height, so the bands never
    cross - the layering stays legible.
    """
    height, width = shape
    y = np.mgrid[0:height, 0:width][0].astype(np.float32) / height
    warp = fbm(shape, rng, cells=2, octaves=3) - 0.5
    index = np.floor((y + warp * 0.26) * layers)
    # 0.34, not 1.0: at full strength the alternating bands read as a flag
    # rather than as a background. The separation comes from the hairline
    # between them, not from the fills.
    return (index % 2 == 0).astype(np.float32) * 0.34, _edges(index)


def _hairline(shape: tuple[int, int]) -> int:
    """Line width in pixels: one at 720p, scaling with the image."""
    return max(1, round(shape[0] / 720))


def _canvas(shape: tuple[int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("L", (shape[1], shape[0]), 0)
    return image, ImageDraw.Draw(image)


def _field(image: Image.Image) -> np.ndarray:
    return np.asarray(image, dtype=np.float32) / 255.0


def aurora(shape, rng, glows: int = 4):
    """A few large soft glows bleeding in from the edges, and no line work.

    Each glow is a wide elliptical gaussian centred off the canvas or near its
    edge, in the second tone; one in three carries the accent, faintly. The
    quiet mask leaves the middle dark, so the light reads as coming from beyond
    the screen.
    """
    height, width = shape
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    fill = np.zeros(shape, dtype=np.float32)
    glow = np.zeros(shape, dtype=np.float32)
    for index in range(glows):
        # Around the edge: a point on a wide ellipse just outside the frame.
        angle = rng.random() * 2 * np.pi
        cx = width / 2 + np.cos(angle) * width * (0.45 + rng.random() * 0.2)
        cy = height / 2 + np.sin(angle) * height * (0.45 + rng.random() * 0.2)
        rx = width * (0.25 + rng.random() * 0.2)
        ry = height * (0.3 + rng.random() * 0.25)
        light = np.exp(-(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2))
        if index % 3 == 2:
            glow = np.maximum(glow, light)
        else:
            fill = np.maximum(fill, light)
    return fill * 0.8, glow * 0.45


def dots(shape, rng, spacing: int = 30):
    """A sparse halftone: a grid of dots sized by a slow field.

    Most of the field sits below the threshold, so most dots are absent and the
    rest gather in loose clusters - a texture that reads at a distance and
    disappears up close.
    """
    height, width = shape
    field = fbm(shape, rng, cells=2, octaves=3)
    step = height / spacing
    largest = step * 0.22
    lines, draw = _canvas(shape)
    for row in range(int(height / step) + 1):
        for column in range(int(width / step) + 1):
            cx, cy = (column + 0.5) * step, (row + 0.5) * step
            value = field[min(int(cy), height - 1), min(int(cx), width - 1)]
            radius = (value - 0.55) / 0.45 * largest
            if radius > step * 0.04:
                draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                             fill=255)
    return np.zeros(shape, dtype=np.float32), _field(lines)


def cells(shape, rng, count: int = 16):
    """Voronoi cells: stained glass with soft fills and lead between them.

    Sites are jittered off a grid rather than scattered, so no cell grows huge
    and none shrinks to a sliver.
    """
    height, width = shape
    columns = max(2, int(np.sqrt(count * width / height)))
    rows = max(2, count // columns)
    gx, gy = np.meshgrid(np.arange(columns), np.arange(rows))
    sx = (gx.ravel() + 0.15 + 0.7 * rng.random(gx.size)) * width / columns
    sy = (gy.ravel() + 0.15 + 0.7 * rng.random(gy.size)) * height / rows
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    index = np.zeros(shape, dtype=np.int32)
    nearest = np.full(shape, np.inf, dtype=np.float32)
    for site, (px, py) in enumerate(zip(sx, sy, strict=True)):
        distance = (x - px) ** 2 + (y - py) ** 2
        closer = distance < nearest
        nearest[closer] = distance[closer]
        index[closer] = site
    levels = rng.choice([0.0, 0.16, 0.3], size=sx.size, p=[0.65, 0.25, 0.1])
    return levels[index].astype(np.float32), _edges(index)


def bubbles(shape, rng, attempts: int = 500):
    """Circle packing: circles of many sizes that never touch.

    Placed largest first, each tried at random positions until it fits, so the
    big ones anchor the composition and the small ones fill the gaps.
    """
    height, width = shape
    placed: list[tuple[float, float, float]] = []
    gap = height / 160
    largest, smallest = height / 5, height / 30
    for attempt in range(attempts):
        radius = largest * (smallest / largest) ** (attempt / attempts)
        x, y = rng.random() * width, rng.random() * height
        if all((x - px) ** 2 + (y - py) ** 2 > (radius + pr + gap) ** 2
               for px, py, pr in placed):
            placed.append((x, y, radius))
    lines, draw_lines = _canvas(shape)
    tone, draw_tone = _canvas(shape)
    width_px = _hairline(shape)
    for x, y, radius in placed:
        box = (x - radius, y - radius, x + radius, y + radius)
        draw_lines.ellipse(box, outline=255, width=width_px)
        if rng.random() < 0.3:
            draw_tone.ellipse(box, fill=255)
    return _field(tone) * 0.3, _field(lines)


def ridges(shape, rng, count: int = 14):
    """Stacked ridgelines lifted by noise, each hiding the ones behind it.

    Drawn back to front, every ridge's silhouette is filled in the base colour
    before its line, so nearer ridges occlude farther ones - which is what
    turns a stack of wiggly lines into a landscape.
    """
    height, width = shape
    peaks = fbm((count, width), rng, cells=3, octaves=4)
    columns = np.arange(width, dtype=np.float32)
    lines, draw_lines = _canvas(shape)
    tone, draw_tone = _canvas(shape)
    width_px = _hairline(shape)
    spacing = height / (count - 2)
    for row in range(count):
        base = spacing * (row + 1)
        # Each ridge spans the full range on its own, then cubed, so most of
        # it lies low and a couple of peaks rise sharply: that contrast is what
        # makes it a ridgeline rather than a stripe.
        profile = peaks[row] - peaks[row].min()
        profile /= max(float(profile.max()), 1e-6)
        lift = profile ** 3 * spacing * 5
        ys = base - lift
        outline = list(zip(columns[::4], ys[::4], strict=True))
        silhouette = [*outline, (width, height), (0, height)]
        # Clear what this ridge hides, then draw it.
        draw_lines.polygon(silhouette, fill=0)
        draw_tone.polygon(silhouette, fill=60 if row % 3 == 0 else 0)
        draw_lines.line(outline, fill=255, width=width_px)
    return _field(tone), _field(lines)


def facets(shape, rng, grid: int = 6):
    """A low-poly mesh: jittered triangles shaded by a slow field.

    Each triangle takes the field's value at its centre, quantised to a few
    levels, so the surface reads as faceted stone rather than a gradient.
    """
    height, width = shape
    columns = int(grid * width / height) + 1
    shade = fbm(shape, rng, cells=2, octaves=3)
    px = (np.arange(columns + 1)[None, :] / columns * width
          + (rng.random((grid + 1, columns + 1)) - 0.5) * width / columns * 0.7)
    py = (np.arange(grid + 1)[:, None] / grid * height
          + (rng.random((grid + 1, columns + 1)) - 0.5) * height / grid * 0.7)
    lines, draw_lines = _canvas(shape)
    tone, draw_tone = _canvas(shape)
    width_px = _hairline(shape)
    for row in range(grid):
        for column in range(columns):
            corners = [(px[row, column], py[row, column]),
                       (px[row, column + 1], py[row, column + 1]),
                       (px[row + 1, column + 1], py[row + 1, column + 1]),
                       (px[row + 1, column], py[row + 1, column])]
            split = (rng.random() < 0.5)
            pairs = ([corners[0], corners[1], corners[2]],
                     [corners[0], corners[2], corners[3]]) if split else (
                    [corners[0], corners[1], corners[3]],
                    [corners[1], corners[2], corners[3]])
            for triangle in pairs:
                cx = int(sum(p[0] for p in triangle) / 3) % width
                cy = int(sum(p[1] for p in triangle) / 3) % height
                level = round(shade[cy, cx] * 4) / 4
                draw_tone.polygon(triangle, fill=int(level * 90))
                draw_lines.polygon(triangle, outline=255, width=width_px)
    return _field(tone), _field(lines) * 0.35


RENDERERS = {"contour": contour, "arcs": arcs, "strata": strata, "aurora": aurora, "dots": dots,
             "cells": cells, "bubbles": bubbles, "ridges": ridges,
             "facets": facets}


# --------------------------------------------------------------------------- #
# composition

def style_for(name: str) -> str:
    """Fall back to a style derived from the theme name.

    Shipped themes name their style explicitly - hashing seven names over three
    styles gave four of one and one of another, which is what hashing does, and
    curating is cheap at this scale. This is for user themes, which have no
    curator.

    crc32 rather than hash(): Python salts hash() per process, so a user theme
    would drift between styles on every regeneration.
    """
    return FALLBACK_STYLES[zlib.crc32(name.encode()) % len(FALLBACK_STYLES)]


def _rng(theme: dict) -> np.random.Generator:
    """The theme's composition: the same for the same name and variation.

    Variation 0 keeps the name alone as the seed, so every wallpaper rendered
    before variations existed stays exactly as it was.
    """
    variation = theme.get("wallpaper_variation", 0)
    key = theme["name"] if not variation else f"{theme['name']}:{variation}"
    return np.random.default_rng(zlib.crc32(key.encode()))


def logo_mask(size: tuple[int, int]) -> np.ndarray | None:
    for path in MASK_PATHS:
        if os.path.exists(path):
            mask = Image.open(path).convert("L")
            width, height = size
            target = int(height * LOGO_HEIGHT)
            scale = target / mask.height
            mask = mask.resize((max(1, round(mask.width * scale)), target),
                               Image.LANCZOS)
            canvas = Image.new("L", (width, height), 0)
            canvas.paste(mask, ((width - mask.width) // 2,
                                (height - mask.height) // 2))
            return np.asarray(canvas, dtype=np.float32) / 255.0
    return None


def compose(theme: dict, size: tuple[int, int] = (WIDTH, HEIGHT),
            style: str | None = None, logo: bool = True) -> Image.Image:
    """Render the wallpaper for a theme as a Pillow image."""
    width, height = size
    shape = (height, width)
    palette = tones(theme)
    style = style or theme.get("wallpaper_style") or style_for(theme["name"])
    if style not in RENDERERS:
        raise ValueError(f"unknown style {style!r}; expected one of "
                         f"{', '.join(STYLES)}")

    rng = _rng(theme)
    fill, line = RENDERERS[style](shape, rng)

    mask = quiet_mask(shape)
    fill *= mask
    line *= mask

    # A slow vertical gradient underneath, so even the quiet centre has depth.
    ramp = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    base = palette["base"] * (1.0 - 0.12 * ramp)[..., None]

    image = base + (palette["shape"] - base) * fill[..., None]
    image = image + (palette["line"] - image) * (
        line * palette["line_alpha"])[..., None]

    if logo:
        ink = logo_mask(size)
        if ink is not None:
            image = image + (palette["ink"] - image) * (ink * LOGO_ALPHA)[..., None]

    return Image.fromarray((np.clip(image, 0, 1) * 255).astype(np.uint8))


def boot_background(theme: dict,
                    size: tuple[int, int] = (1920, 1080)) -> Image.Image:
    """A quieter version for the boot menu.

    The desktop wallpaper is too busy to put menu text on. This keeps the
    palette and the gradient but drops the pattern to a quarter strength and
    leaves the mark off entirely - GRUB places the logo itself, as its own
    component, so it stays crisp instead of being resampled with the
    background.
    """
    width, height = size
    palette = tones(theme)
    style = theme.get("wallpaper_style") or style_for(theme["name"])
    rng = _rng(theme)
    fill, line = RENDERERS[style]((height, width), rng)

    mask = quiet_mask((height, width))
    fill *= mask * 0.25
    line *= mask * 0.25

    ramp = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    base = palette["base"] * (1.0 - 0.18 * ramp)[..., None]
    image = base + (palette["shape"] - base) * fill[..., None]
    image = image + (palette["line"] - image) * (
        line * palette["line_alpha"])[..., None]
    return Image.fromarray((np.clip(image, 0, 1) * 255).astype(np.uint8))


def render(theme: dict, dest: str, size: tuple[int, int] = (WIDTH, HEIGHT),
           style: str | None = None) -> str:
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    compose(theme, size, style).save(dest)
    return dest


# --------------------------------------------------------------------------- #
# cli

def _load(name: str) -> dict:
    path = name if name.endswith(".json") else os.path.join(HERE, f"{name}.json")
    if not os.path.exists(path):
        sys.exit(f"no such theme: {path}")
    with open(path) as fh:
        return json.load(fh)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("themes", nargs="*")
    parser.add_argument("--style", choices=STYLES)
    parser.add_argument("--show-styles", action="store_true",
                        help="render every style for each theme, for comparison")
    parser.add_argument("--size", default=f"{WIDTH}x{HEIGHT}")
    parser.add_argument("--out", default=OUT)
    parser.add_argument("--no-logo", action="store_true")
    args = parser.parse_args()

    width, height = (int(v) for v in args.size.lower().split("x"))
    names = args.themes or sorted(
        f[:-5] for f in os.listdir(HERE) if f.endswith(".json"))

    for name in names:
        theme = _load(name)
        styles = STYLES if args.show_styles else (args.style,)
        for style in styles:
            suffix = f"-{style}" if args.show_styles else ""
            dest = os.path.join(args.out, f"{theme['name']}{suffix}.png")
            os.makedirs(args.out, exist_ok=True)
            compose(theme, (width, height), style,
                    logo=not args.no_logo).save(dest)
            print(f"  {dest}")


if __name__ == "__main__":
    main()
