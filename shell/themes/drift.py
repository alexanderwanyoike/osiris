"""Tell the drift extension how to draw the active theme's moving wallpaper.

    python3 shell/themes/drift.py              # runs for the session
    python3 shell/themes/drift.py --once       # publish once and exit

Started at login by /etc/xdg/autostart/osiris-drift.desktop. When the active
theme's style is a wallpaper package (osiris/themes/wallpapers.py), the
drift@osiris Cinnamon extension draws its shader live on the GPU, every frame,
so the wallpaper genuinely moves. What it needs from here goes in STATE: the
theme's colours, whatever the package's still.py hands its shader, the Osiris
mark as an overlay, and - if the shader would not compile or still.py fails -
the problem instead, so the still wallpaper stays and Appearance can say why.

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

# wallpaper has put the osiris package on sys.path.
from osiris.platform.hardware import rendering_accelerated  # noqa: E402
from osiris.platform import RealFileSystem  # noqa: E402
from osiris.platform.process import SubprocessRunner  # noqa: E402
from osiris.provision.upgrade import Upgrade  # noqa: E402
from osiris.themes import wallpapers as packages  # noqa: E402

POLL = 2
# Points round the loop at which a package's ranges() are measured; the
# extension interpolates between them.
RANGE_SAMPLES = 48

PREFERENCE = os.path.join(home(), ".config", "osiris", "drift")
CACHE = os.path.join(home(), ".cache", "osiris", "drift")
STATE = os.path.join(CACHE, "current.json")
# Written by the extension when drawing live costs more than the machine has.
UNSUPPORTED = os.path.join(CACHE, "unsupported")
NO_GPU = "Moving wallpapers need a graphics card; showing the still one instead."
PRELUDE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "wallpapers", "prelude.glsl")

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


def package(theme: dict) -> packages.Wallpaper | None:
    """The wallpaper package the theme's style names, if it is one."""
    found, _ = packages.discover(wallpaper.PACKAGE_DIRS)
    return found.get(style_of(theme) or "")


def drifts(theme: dict) -> bool:
    return package(theme) is not None


def problem() -> str | None:
    """Why the wallpaper is not moving, when something went wrong."""
    try:
        with open(UNSUPPORTED) as fh:
            return fh.read().strip() or None
    except OSError:
        pass
    try:
        with open(STATE) as fh:
            return json.load(fh).get("problem")
    except (OSError, ValueError):
        return None


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
    os.makedirs(CACHE, exist_ok=True)
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


def palette(theme: dict) -> dict:
    """The theme as every shader sees it; prelude.glsl declares these."""
    tones = wallpaper.tones(theme)
    colours = theme["colors"]
    uniforms = {f"u_{key}": [3, floats(tones[key])]
                for key in ("base", "shape", "line", "ink")}
    for key in ("background", "surface", "foreground", "accent", "accentMuted",
                "success", "warning", "danger"):
        name = "u_" + "".join("_" + c.lower() if c.isupper() else c for c in key)
        uniforms[name] = [3, floats(wallpaper.to_rgb(colours[key]))]
    uniforms["u_line_alpha"] = [1, [float(tones["line_alpha"])]]
    uniforms["u_dark"] = [1, [1.0 if theme.get("dark", True) else 0.0]]
    return uniforms


def stamp(found: packages.Wallpaper) -> float:
    """When the package last changed; an agent may be editing it as it shows."""
    return max(p.stat().st_mtime for p in found.directory.iterdir() if p.is_file())


def state(theme: dict, size: tuple[int, int], accelerated: bool = True) -> dict:
    found = package(theme)
    assert found is not None
    current = {"theme": theme["name"], "style": found.name, "loop": found.loop,
               "stamp": stamp(found), "size": list(size),
               "accelerated": accelerated,
               "prelude": PRELUDE, "shader": str(found.shader),
               "uniforms": palette(theme), "ranges": None,
               "logo": logo(theme, size), "problem": None}
    if not accelerated:
        current["problem"] = NO_GPU
        return current
    try:
        with open(PRELUDE) as fh:
            prelude = fh.read()
        current["problem"] = packages.check(
            found, prelude, SubprocessRunner(sink=lambda line: None))
        if current["problem"] is None:
            # A package's own code: it may be one an agent has just written,
            # so whatever it raises is reported rather than fatal.
            module = wallpaper.still_module(found)
            if hasattr(module, "uniforms"):
                current["uniforms"].update(module.uniforms(theme, size))
            if hasattr(module, "ranges"):
                phases = [i / RANGE_SAMPLES * 2 * math.pi
                          for i in range(RANGE_SAMPLES)]
                current["ranges"] = module.ranges(theme, size, phases)
    except Exception as error:                          # noqa: BLE001
        current["problem"] = f"{found.still.name}: {error}"
    return current


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


def publish_now(theme: dict) -> None:
    """Publish for `theme` at once, rather than at the next poll.

    For a theme switch, which wants the moving wallpaper changed beneath its
    frozen picture. Runs in the switching process, so it reuses the screen
    size and the GPU answer this process found at login instead of asking a
    display again.
    """
    if not enabled() or not drifts(theme):
        return
    try:
        with open(STATE) as fh:
            previous = json.load(fh)
    except (OSError, ValueError):
        previous = {}
    size = tuple(previous.get("size") or FALLBACK_SIZE)
    publish(state(theme, (int(size[0]), int(size[1])),
                  previous.get("accelerated", True)))


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
    # Asked once a session: drawing on the CPU every frame costs more than a
    # moving wallpaper is worth, so such a machine keeps the still one.
    accelerated = rendering_accelerated(SubprocessRunner(sink=lambda line: None))
    last: tuple[object, dict | None] = (None, None)
    upgrade = Upgrade(RealFileSystem())
    while True:
        if upgrade.happened():
            os.execv(sys.executable, [sys.executable, *sys.argv])
        try:
            theme = wanted()
            # Worked out again only when the theme or its package changes; a
            # package's ranges can take a moment.
            found = package(theme) if theme is not None else None
            key = (theme, stamp(found)) if found is not None else None
            if theme is not None and key != last[0]:
                last = (key, state(theme, size, accelerated))
                publish(last[1])
        except Exception as error:                      # noqa: BLE001
            print(f"osiris-drift: {error}", file=sys.stderr)
        if args.once:
            return
        time.sleep(POLL)


if __name__ == "__main__":
    main()
