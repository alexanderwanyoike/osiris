"""Render the active theme's drifting wallpaper as a loop of frames.

    python3 shell/themes/drift.py              # runs for the session
    python3 shell/themes/drift.py --once       # render the current loop and exit

Started at login by /etc/xdg/autostart/osiris-drift.desktop. When the active
theme's wallpaper is one of the DRIFTING styles, this renders COUNT frames
round its phase (wallpaper.compose) at the screen's size and publishes them in
STATE. The drift@osiris Cinnamon extension plays them by the clock, blending
each frame into the next, so the wallpaper is always moving; this process only
draws, once per theme.

The frame due now is rendered first (osiris/themes/frames.py), so playback
starts within seconds of a theme being applied. Only the current theme's
frames are kept.

Off when ~/.config/osiris/drift says "off"; the extension reads that itself,
so switching it off is immediate.
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import preview  # noqa: E402
import wallpaper  # noqa: E402
from paths import home  # noqa: E402

for candidate in (
    "/usr/share/osiris/lib",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
):
    if os.path.isdir(os.path.join(candidate, "osiris")):
        sys.path.insert(0, candidate)
        break

from osiris.themes.frames import render_order  # noqa: E402

# Calm, but visibly moving: all the way round in ten minutes, a new frame
# every five seconds, each blended into the next for the whole five.
LOOP = 10 * 60
COUNT = 120
POLL = 5

PREFERENCE = os.path.join(home(), ".config", "osiris", "drift")
CACHE = os.path.join(home(), ".cache", "osiris", "drift")
# What the extension plays: {"theme", "dir", "count", "loop"}.
STATE = os.path.join(CACHE, "current.json")
# Where the previous design pointed the desktop background; put back on start.
STILL_FRAMES = os.path.join(home(), ".local", "share", "osiris", "drift")

# The styles that drift; the rest stay still. Chosen for how they move, not
# for whether they can: a slowly turning contour or facet mesh reads as
# restlessness, where these read as light, weather and terrain.
DRIFTING = ("aurora", "dots", "ridges", "cells", "wave")

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


def drifts(theme: dict) -> bool:
    named = theme.get("wallpaper")
    if named and named != "generated":
        return False
    style = theme.get("wallpaper_style") or wallpaper.style_for(theme["name"])
    return style in DRIFTING


def screen_size() -> tuple[int, int]:
    """The largest monitor, in device pixels; frames are drawn to fill it."""
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


def key(theme: dict, size: tuple[int, int]) -> str:
    """Names a loop by everything that changes what it looks like."""
    look = {k: theme.get(k) for k in (
        "name", "colors", "dark", "wallpaper_style", "wallpaper_variation")}
    look.update(size=list(size), count=COUNT,
                renderer=preview.RENDERER_VERSION)
    digest = hashlib.sha1(json.dumps(look, sort_keys=True).encode())
    return digest.hexdigest()[:16]


def frame_path(directory: str, index: int) -> str:
    return os.path.join(directory, f"frame-{index:03d}.jpg")


def publish(theme: dict, directory: str) -> None:
    state = {"theme": theme["name"], "dir": directory,
             "count": COUNT, "loop": LOOP}
    try:
        with open(STATE) as fh:
            if json.load(fh) == state:
                return
    except (OSError, ValueError):
        pass
    temporary = STATE + ".tmp"
    with open(temporary, "w") as fh:
        json.dump(state, fh)
    os.replace(temporary, STATE)


def forget_others(keep: str) -> None:
    for name in os.listdir(CACHE):
        path = os.path.join(CACHE, name)
        if os.path.isdir(path) and path != keep:
            shutil.rmtree(path, ignore_errors=True)


def render(theme: dict, size: tuple[int, int],
           still_wanted=lambda: True) -> None:
    """Render whichever frames of the theme's loop are missing.

    `still_wanted` is asked between frames, so a theme switched away from
    mid-render stops costing anything.
    """
    directory = os.path.join(CACHE, key(theme, size))
    os.makedirs(directory, exist_ok=True)
    publish(theme, directory)
    forget_others(directory)
    for index in render_order(time.time(), LOOP, COUNT):
        path = frame_path(directory, index)
        if os.path.exists(path):
            continue
        if not still_wanted():
            return
        image = wallpaper.compose(theme, size,
                                  phase=index / COUNT * 2 * math.pi)
        # Written aside and moved into place, so the extension never loads a
        # half-written frame. Full chroma keeps the accent hairlines crisp.
        temporary = path + ".tmp"
        image.save(temporary, "JPEG", quality=92, subsampling=0)
        os.replace(temporary, path)


def _put_back_still() -> None:
    result = subprocess.run(
        ["dconf", "read", "/org/cinnamon/desktop/background/picture-uri"],
        check=False, capture_output=True, text=True, env=engine._session_env())
    name = engine.current()
    if STILL_FRAMES in result.stdout and name is not None:
        subprocess.run(
            ["dconf", "write", "/org/cinnamon/desktop/background/picture-uri",
             f"'file://{engine.wallpaper_for(engine.load(name))}'"],
            check=False, capture_output=True, env=engine._session_env())


def wanted() -> dict | None:
    """The theme whose loop should exist now, if any."""
    name = engine.current()
    if name is None or not enabled():
        return None
    theme = engine.load(name)
    return theme if drifts(theme) else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true",
                        help="render the current loop and exit")
    args = parser.parse_args()

    # Rendering is background work; the desktop it draws for comes first.
    os.nice(10)
    _put_back_still()
    os.makedirs(CACHE, exist_ok=True)
    size = screen_size()
    while True:
        try:
            theme = wanted()
            if theme is not None:
                name = theme["name"]
                render(theme, size, still_wanted=lambda n=name: (
                    (now := wanted()) is not None and now["name"] == n))
        except Exception as error:                      # noqa: BLE001
            print(f"osiris-drift: {error}", file=sys.stderr)
        if args.once:
            return
        time.sleep(POLL)


if __name__ == "__main__":
    main()
