"""Let the active theme's generated wallpaper drift, slowly.

    python3 shell/themes/drift.py              # runs for the session
    python3 shell/themes/drift.py --once       # render and show one frame

Started at login by /etc/xdg/autostart/osiris-drift.desktop. Every INTERVAL it
renders the wallpaper a little further round its phase (wallpaper.compose) and
points the desktop at it; Cinnamon crossfades from one background to the next,
so the wallpaper moves without anything here drawing on screen.

The phase comes from the clock, so it carries on across logins rather than
starting again, and a full turn takes LOOP. A wallpaper that is a picture or a
named file does not drift, and neither do styles with no field to turn.

Off when ~/.config/osiris/drift says "off"; switching it off puts the still
wallpaper back.
"""
import argparse
import math
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import wallpaper  # noqa: E402
from paths import home  # noqa: E402

# Slow enough to be calm, often enough that the desktop is visibly alive: a
# new frame every three minutes, all the way round in four hours.
INTERVAL = 180
LOOP = 4 * 60 * 60

PREFERENCE = os.path.join(home(), ".config", "osiris", "drift")
FRAMES = os.path.join(home(), ".local", "share", "osiris", "drift")

# Styles whose drawing has no field to turn; their frames would all be alike.
STILL_STYLES = ("arcs", "bubbles")


def enabled() -> bool:
    try:
        with open(PREFERENCE) as fh:
            return fh.read().strip() != "off"
    except OSError:
        return True


def phase(now: float) -> float:
    return (now % LOOP) / LOOP * 2 * math.pi


def drifts(theme: dict) -> bool:
    named = theme.get("wallpaper")
    if named and named != "generated":
        return False
    style = theme.get("wallpaper_style") or wallpaper.style_for(theme["name"])
    return style not in STILL_STYLES


def show(path: str) -> None:
    # One key, so one change: Cinnamon fades the old background into this one.
    subprocess.run(
        ["dconf", "write", "/org/cinnamon/desktop/background/picture-uri",
         f"'file://{path}'"],
        check=False, capture_output=True, env=engine._session_env())


def frame(theme: dict, turn: float, slot: int) -> str:
    """Render the frame at `turn` into one of two files, alternately.

    The file name has to change for Cinnamon to load and fade to it; writing
    over the file it already shows changes nothing on screen.
    """
    os.makedirs(FRAMES, exist_ok=True)
    path = os.path.join(FRAMES, f"frame-{slot}.png")
    image = wallpaper.compose(theme, (wallpaper.WIDTH, wallpaper.HEIGHT),
                              phase=turn)
    image.save(path)
    return path


def step(slot: int, last: tuple[str | None, float | None]) -> tuple[str | None, float | None]:
    """One tick: show the next frame if the active theme drifts."""
    name = engine.current()
    if name is None:
        return last
    theme = engine.load(name)
    if not enabled() or not drifts(theme):
        if last[0] is not None:
            show(engine.wallpaper_for(theme))       # back to the still one
        return (None, None)
    turn = phase(time.time())
    if last == (name, turn):
        return last
    show(frame(theme, turn, slot))
    return (name, turn)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true",
                        help="show one frame and exit")
    args = parser.parse_args()

    last: tuple[str | None, float | None] = (None, None)
    slot = 0
    while True:
        try:
            last = step(slot, last)
        except Exception as error:                      # noqa: BLE001
            print(f"osiris-drift: {error}", file=sys.stderr)
        if args.once:
            return
        slot = 1 - slot
        time.sleep(INTERVAL - time.time() % INTERVAL)


if __name__ == "__main__":
    main()
