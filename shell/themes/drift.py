"""Tell the drift extension how to draw the active theme's moving wallpaper.

    python3 shell/themes/drift.py              # runs for the session
    python3 shell/themes/drift.py --once       # publish once and exit

Started at login by /etc/xdg/autostart/osiris-drift.desktop. The drift@osiris
Cinnamon extension draws a DRIFTING style live on the GPU, every frame, so the
wallpaper genuinely moves rather than dissolving between stills. What it needs
from here is what only the Python side knows: the theme's tones and the
style's composition, drawn from the same generator as the still wallpaper
(wallpaper.tones, wallpaper.wave_shape), plus the Osiris mark as an overlay.
These go in STATE; the extension follows that file.

Off when ~/.config/osiris/drift says "off"; the extension reads that itself,
so switching it off is immediate.
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import wallpaper  # noqa: E402
from paths import home  # noqa: E402

# Seconds for a full turn of each style. Calm, but always visibly moving: the
# wave's faster ribbons turn two and three times per loop, so it can take
# longest; glows and cells move one turn per loop, so they need less.
LOOPS = {"wave": 90, "aurora": 60, "cells": 60, "dots": 120, "ridges": 120}
POLL = 2
# Points round the loop at which a noise style's range is measured; the
# extension interpolates between them.
RANGE_SAMPLES = 48

PREFERENCE = os.path.join(home(), ".config", "osiris", "drift")
CACHE = os.path.join(home(), ".cache", "osiris", "drift")
STATE = os.path.join(CACHE, "current.json")

# The styles the extension can draw live; the shader in drift@osiris has each.
# Others stay still: blending between pre-rendered stills was tried and reads
# as a slideshow, not as movement.
DRIFTING = tuple(LOOPS)

FALLBACK_SIZE = (1920, 1080)


def enabled() -> bool:
    try:
        with open(PREFERENCE) as fh:
            return fh.read().strip() != "off"
    except OSError:
        return True


def set_enabled(on: bool) -> None:
    os.makedirs(os.path.dirname(PREFERENCE), exist_ok=True)
    with open(PREFERENCE, "w") as fh:
        fh.write("on\n" if on else "off\n")


def style_of(theme: dict) -> str | None:
    named = theme.get("wallpaper")
    if named and named != "generated":
        return None
    return theme.get("wallpaper_style") or wallpaper.style_for(theme["name"])


def drifts(theme: dict) -> bool:
    return style_of(theme) in DRIFTING


def screen_size() -> tuple[int, int]:
    """The largest monitor, in device pixels; the mark is drawn to fill it."""
    try:
        import gi
        gi.require_version("Gdk", "4.0")
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gdk, Gtk
    except (ImportError, ValueError):
        return FALLBACK_SIZE
    if not Gtk.init_check():
        return FALLBACK_SIZE
    sizes = []
    for monitor in Gdk.Display.get_default().get_monitors():
        geometry, scale = monitor.get_geometry(), monitor.get_scale_factor()
        sizes.append((geometry.width * scale, geometry.height * scale))
    return max(sizes, key=lambda s: s[0] * s[1]) if sizes else FALLBACK_SIZE


def logo(theme: dict, size: tuple[int, int]) -> str | None:
    """The Osiris mark in the theme's ink, transparent elsewhere.

    Drawn over the live wallpaper the way compose() draws it over the still
    one, so the mark does not vanish while the wallpaper moves.
    """
    mask = wallpaper.logo_mask(size)
    if mask is None:
        return None
    ink = wallpaper.tones(theme)["ink"]
    digest = hashlib.sha1(json.dumps([list(ink), list(size)]).encode())
    path = os.path.join(CACHE, f"logo-{digest.hexdigest()[:12]}.png")
    if not os.path.exists(path):
        rgba = np.zeros((size[1], size[0], 4), dtype=np.uint8)
        rgba[..., :3] = (ink * 255).astype(np.uint8)
        rgba[..., 3] = (mask * wallpaper.LOGO_ALPHA * 255).astype(np.uint8)
        temporary = path + ".tmp"
        Image.fromarray(rgba, "RGBA").save(temporary, "PNG")
        os.replace(temporary, path)
    for name in os.listdir(CACHE):
        if name.startswith("logo-") and os.path.join(CACHE, name) != path:
            os.remove(os.path.join(CACHE, name))
    return path


def floats(values) -> list[float]:
    return [float(v) for v in np.ravel(values)]


def lattices(found: list) -> tuple[list[float], list[float]]:
    """Every octave's lattice, and every partner, each run end to end."""
    return (floats(np.concatenate([a.ravel() for a, _ in found])),
            floats(np.concatenate([b.ravel() for _, b in found])))


def turns() -> list[float]:
    return [i / RANGE_SAMPLES * 2 * math.pi for i in range(RANGE_SAMPLES)]


def composition(theme: dict, style: str,
                size: tuple[int, int]) -> tuple[dict, list | None]:
    """The style's uniforms, and its range at RANGE_SAMPLES points if noise.

    Drawn from the same generators, in the same order, as the style's renderer
    in wallpaper.py, so the live wallpaper is the still one set moving.
    """
    rng = wallpaper._rng(theme)
    drift = wallpaper._rng(theme, "drift")
    if style == "wave":
        tilt, offsets = wallpaper.wave_shape(rng)
        return {"u_tilt": [1, [float(tilt)]],
                "u_offsets": [1, floats(offsets)]}, None
    if style == "aurora":
        glows = wallpaper.aurora_shape(rng, drift=drift)
        return {"u_glow_a": [4, floats([[g["angle"], g["turn"], g["fx"], g["fy"]]
                                        for g in glows])],
                "u_glow_b": [4, floats([[g["rx"], g["ry"], 0, 0]
                                        for g in glows])]}, None
    if style == "cells":
        sites = wallpaper.cells_shape(rng, size[0] / size[1], drift=drift)
        packed = np.stack([sites["x"], sites["y"], sites["turn"],
                           sites["levels"]], axis=1)
        return {"u_sites": [4, floats(packed)],
                "u_cells": [2, [float(len(packed)), float(sites["rows"])]]}, None
    if style == "dots":
        found = wallpaper.fbm_lattices(rng, 2, 3, drift)
        lattice, partner = lattices(found)
        small = (size[1] // 4, size[0] // 4)
        ranges = [[float(f.min()), float(f.max())] for f in (
            wallpaper.fbm_raw(small, found, phase=turn) for turn in turns())]
        return {"u_lat": [4, lattice], "u_par": [4, partner]}, ranges
    # ridges: fbm over (count, width), so each ridge is one row of it. The
    # rows are interpolated here, once; the shader only interpolates along x.
    count = 14
    found = wallpaper.fbm_lattices(rng, 3, 4, drift)
    rows = [(wallpaper._smooth(a, (count, a.shape[1])),
             wallpaper._smooth(b, (count, b.shape[1]))) for a, b in found]
    lattice, partner = lattices(rows)
    ranges = []
    for turn in turns():
        raw = wallpaper.fbm_raw((count, 640), found, phase=turn)
        ranges.append(floats(np.stack([raw.min(axis=1), raw.max(axis=1)],
                                      axis=1)))
    return {"u_rl": [4, lattice], "u_rp": [4, partner]}, ranges


def state(theme: dict, size: tuple[int, int]) -> dict:
    tones = wallpaper.tones(theme)
    style = style_of(theme)
    uniforms, ranges = composition(theme, style, size)
    return {
        "theme": theme["name"],
        "style": style,
        "loop": LOOPS[style],
        "uniforms": {
            "u_base": [3, floats(tones["base"])],
            "u_shape": [3, floats(tones["shape"])],
            "u_line": [3, floats(tones["line"])],
            "u_line_alpha": [1, [float(tones["line_alpha"])]],
            "u_reach": [1, [float(wallpaper.QUIET_REACH.get(
                style, wallpaper.QUIET_RADIUS))]],
            **uniforms,
        },
        "ranges": ranges,
        "logo": logo(theme, size),
    }


def publish(current: dict) -> None:
    try:
        with open(STATE) as fh:
            if json.load(fh) == current:
                return
    except (OSError, ValueError):
        pass
    temporary = STATE + ".tmp"
    with open(temporary, "w") as fh:
        json.dump(current, fh)
    os.replace(temporary, STATE)


def wanted() -> dict | None:
    """The theme whose wallpaper should be moving now, if any."""
    name = engine.current()
    if name is None or not enabled():
        return None
    theme = engine.load(name)
    return theme if drifts(theme) else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true",
                        help="publish once and exit")
    args = parser.parse_args()

    os.makedirs(CACHE, exist_ok=True)
    # Loops of pre-rendered frames, from when the wallpaper was played as a
    # slideshow; nothing reads them now.
    for name in os.listdir(CACHE):
        if os.path.isdir(os.path.join(CACHE, name)):
            shutil.rmtree(os.path.join(CACHE, name), ignore_errors=True)
    size = screen_size()
    last: tuple[dict | None, dict | None] = (None, None)
    while True:
        try:
            theme = wanted()
            # Worked out again only when the theme changes; the noise styles'
            # ranges take a moment.
            if theme is not None and theme != last[0]:
                last = (theme, state(theme, size))
                publish(last[1])
        except Exception as error:                      # noqa: BLE001
            print(f"osiris-drift: {error}", file=sys.stderr)
        if args.once:
            return
        time.sleep(POLL)


if __name__ == "__main__":
    main()
