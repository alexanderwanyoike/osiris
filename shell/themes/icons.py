"""Tint the folder icons to match a palette.

Papirus already ships its folders in two dozen colours - `folder-blue.svg`,
`folder-teal.svg` and so on, plus a variant of every semantic folder
(`folder-blue-documents.svg`). The work here is choosing which of those a
palette wants, not drawing anything: picking the nearest shipped colour to the
theme's accent and assembling an icon theme that points at it.

That matters. Recolouring an icon set is the same trap as writing a GTK theme -
a permanent maintenance cost against an upstream that keeps moving. Nothing
here is drawn, generated or patched; every file referenced belongs to
papirus-icon-theme and is reached by symlink.

The generated theme inherits the real one, so everything except folders falls
through untouched:

    ~/.icons/Osiris-<palette>/
        index.theme                 Inherits=Papirus-Dark
        <size>/places/folder.svg    -> Papirus/<size>/places/folder-teal.svg

`user-home.svg` and `user-desktop.svg` are left alone: Papirus ships no colour
variants of them, and a tinted folder beside an untinted house looks worse than
leaving both as they came.
"""
import colorsys
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import home  # noqa: E402

PAPIRUS = "/usr/share/icons/Papirus"
ICONS_DIR = os.path.join(home(), ".icons")
PREFIX = "Osiris-"

# The sizes Papirus ships folders in.
SIZES = (16, 22, 24, 32, 48, 64)

# Papirus's base folder colours, read off the face of each shipped SVG. Only
# the ones that name a colour - the rest (`folder-git`, `folder-steam`) are
# branding and all share the default blue.
FOLDER_COLOURS = {
    "black": "#4f4f4f", "blue": "#5294e2", "bluegrey": "#607d8b",
    "breeze": "#57b8ec", "brown": "#ae8e6c", "carmine": "#a30002",
    "cyan": "#00bcd4", "darkcyan": "#45abb7", "deeporange": "#eb6637",
    "green": "#87b158", "grey": "#8e8e8e", "indigo": "#5c6bc0",
    "magenta": "#ca71df", "nordic": "#81a1c1", "orange": "#ee923a",
    "palebrown": "#d1bfae", "paleorange": "#eeca8f", "pink": "#f06292",
    "red": "#e25252", "teal": "#16a085", "violet": "#7e57c2",
    "white": "#e4e4e4", "yellow": "#f9bd30", "adwaita": "#93c0ea",
}

# Semantic folders worth covering: the ones a file manager actually shows.
# Every one of these exists as folder-<colour>-<name>.svg for every colour.
SEMANTIC = (
    "documents", "download", "downloads", "music", "pictures", "photo",
    "video", "videos", "desktop", "public", "templates", "projects",
    "development", "code", "games", "important", "favorites", "recent",
    "remote", "network", "print", "script", "mail", "notes", "books",
)


def _rgb(value: str) -> tuple[float, float, float]:
    v = value.lstrip("#")
    return tuple(int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _hls(value: str) -> tuple[float, float, float]:
    r, g, b = _rgb(value)
    return colorsys.rgb_to_hls(r, g, b)


def _distance(a: str, b: str) -> float:
    """How far apart two colours are, for the purpose of naming a family.

    Compared in hue, saturation and lightness rather than in RGB. Straight RGB
    distance chose badly on exactly the palettes that need this most: Nord's
    pale cyan came out as a generic blue, and Rose Pine Dawn's muted mauve came
    out as grey, because RGB weighs lightness as heavily as hue.

    The hue term is scaled by the *lesser* of the two saturations, because hue
    is meaningless in a near-grey. That alone is not enough: it hands every
    achromatic candidate a free pass on hue, so a muted mauve accent matched
    `folder-grey` rather than `folder-violet`. The last term is the correction -
    an asymmetric penalty for a candidate duller than the accent. Picking a
    greyer folder than the palette asked for is a visible mistake; picking a
    slightly more saturated one is not.
    """
    h1, l1, s1 = _hls(a)
    h2, l2, s2 = _hls(b)
    hue = abs(h1 - h2)
    hue = min(hue, 1.0 - hue)                     # hue is a circle
    return (20.0 * hue ** 2 * min(s1, s2)
            + 1.0 * (s1 - s2) ** 2
            + 0.5 * (l1 - l2) ** 2
            + 3.0 * max(0.0, s1 - s2) ** 2)


def folder_colour(theme: dict) -> str:
    """Which Papirus folder colour this theme wants.

    A theme may name one in `folder_colour`; the shipped ones do, because
    curating seven values is exact and free, and a heuristic is neither. The
    match is the fallback, for themes written on the machine.
    """
    declared = theme.get("folder_colour")
    if declared in FOLDER_COLOURS:
        return declared
    return nearest(theme["colors"]["accent"])


def nearest(accent: str) -> str:
    """The Papirus folder colour closest to this accent."""
    return min(FOLDER_COLOURS, key=lambda name: _distance(accent,
                                                          FOLDER_COLOURS[name]))


def _index_theme(name: str, base: str) -> str:
    directories = ",".join(f"{size}x{size}/places" for size in SIZES)
    sections = "".join(
        f"\n[{size}x{size}/places]\nSize={size}\nContext=Places\nType=Fixed\n"
        for size in SIZES)
    return (f"[Icon Theme]\n"
            f"Name={name}\n"
            f"Comment=Osiris folder tint over {base}\n"
            f"Inherits={base},hicolor\n"
            f"Directories={directories}\n"
            f"{sections}")


def theme_name(theme: dict) -> str:
    return PREFIX + theme["name"]


def build(theme: dict, base: str) -> str | None:
    """Assemble the icon theme for a palette. Returns its name, or None.

    None means Papirus is not installed, in which case the caller should fall
    back to the theme's declared icon set rather than pointing the desktop at
    a theme that does not exist.
    """
    if not os.path.isdir(PAPIRUS):
        return None
    colour = folder_colour(theme)
    name = theme_name(theme)
    root = os.path.join(ICONS_DIR, name)

    try:
        if os.path.isdir(root):
            shutil.rmtree(root)
        for size in SIZES:
            source_dir = os.path.join(PAPIRUS, f"{size}x{size}", "places")
            if not os.path.isdir(source_dir):
                continue
            target_dir = os.path.join(root, f"{size}x{size}", "places")
            os.makedirs(target_dir, exist_ok=True)

            wanted = [("folder.svg", f"folder-{colour}.svg")]
            wanted += [(f"folder-{s}.svg", f"folder-{colour}-{s}.svg")
                       for s in SEMANTIC]
            for link_name, source_name in wanted:
                source = os.path.join(source_dir, source_name)
                if not os.path.exists(source):
                    continue
                os.symlink(source, os.path.join(target_dir, link_name))

        with open(os.path.join(root, "index.theme"), "w") as fh:
            fh.write(_index_theme(name, base))
    except OSError:
        shutil.rmtree(root, ignore_errors=True)
        return None

    for entry in os.listdir(ICONS_DIR):
        if entry.startswith(PREFIX) and entry != name:
            shutil.rmtree(os.path.join(ICONS_DIR, entry), ignore_errors=True)
    return name
