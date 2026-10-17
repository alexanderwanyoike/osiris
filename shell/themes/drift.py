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

# A full turn of the wave's slowest ribbon. Its others turn two and three
# times as fast, so something is always visibly moving without hurrying.
LOOP = 90
POLL = 2

PREFERENCE = os.path.join(home(), ".config", "osiris", "drift")
CACHE = os.path.join(home(), ".cache", "osiris", "drift")
STATE = os.path.join(CACHE, "current.json")

# The styles the extension can draw live. Others stay still until they have a
# shader: blending between pre-rendered stills was tried and reads as a
# slideshow, not as movement.
DRIFTING = ("wave",)

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


def state(theme: dict, size: tuple[int, int]) -> dict:
    tones = wallpaper.tones(theme)
    tilt, offsets = wallpaper.wave_shape(wallpaper._rng(theme))
    return {
        "theme": theme["name"],
        "style": style_of(theme),
        "loop": LOOP,
        "base": [float(v) for v in tones["base"]],
        "shape": [float(v) for v in tones["shape"]],
        "line": [float(v) for v in tones["line"]],
        "line_alpha": tones["line_alpha"],
        "reach": wallpaper.QUIET_REACH.get("wave", wallpaper.QUIET_RADIUS),
        "tilt": float(tilt),
        "offsets": [float(v) for ribbon in offsets for v in ribbon],
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
    while True:
        try:
            theme = wanted()
            if theme is not None:
                publish(state(theme, size))
        except Exception as error:                      # noqa: BLE001
            print(f"osiris-drift: {error}", file=sys.stderr)
        if args.once:
            return
        time.sleep(POLL)


if __name__ == "__main__":
    main()
