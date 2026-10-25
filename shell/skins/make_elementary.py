"""Make the elementary skinpack from elementary's upstream stylesheet.

    git clone https://github.com/elementary/stylesheet /some/where
    python3 shell/skins/make_elementary.py /some/where

Rewrites shell/skins/elementary/. Run again to follow an upstream release;
nothing here runs when a person wears the Skin (ADR 0019).

Upstream's meson build compiles src/gtk-<version>/variants/<accent>[-dark].scss
with sassc, one sheet per accent. A variant only defines the accent shades and
`$color-scheme`, then imports the palette and the index; this pack has one
entry per light and dark whose accent is the Theme's.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parent / "elementary"
VERSIONS = ("gtk-3.0", "gtk-4.0")

# elementary's named hues that carry a role; the rest stay upstream's.
RAMPS = {
    "STRAWBERRY": "$gap-danger",
    "BANANA": "$gap-warning",
    "LIME": "$gap-success",
    "BLUEBERRY": "$gap-accent",
}

# Upstream's steps around the colour a variant uses, as lightness scaled
# towards white or black, so a Theme colour of any lightness gets a full ramp.
RAMP_FUNCTION = """\
// Osiris: the role hues below are ramps around the Theme's colours.
@import '../gaps';

@function gap-ramp($colour, $level) {
    $steps: (100: 35%, 300: 12%, 500: -15%, 700: -40%, 900: -55%);
    @return scale-color($colour, $lightness: map-get($steps, $level));
}

"""

# Replaces upstream's surface block. Views take the Theme's surface and windows
# its background; sidebars and title bars keep elementary's steps below the
# window, the darker band that makes the look elementary's.
SURFACES = """\
// Osiris: elementary's surfaces, rebuilt from the Theme's colours.
$titlebar-color: mix($gap-foreground, $gap-background, 12%);
$sidebar-color: mix($gap-foreground, $gap-background, 4%);
$input-color: $gap-background;

$fg-color: $gap-foreground;
$toplevel-border-color: rgba(black, 0.2);
$border-color: rgba(black, 0.2);
$insensitive-base-color: rgba(0, 0, 0, 0.03);
$disabled-opacity: 0.5;

$error-color: $gap-danger;
$success-color: $gap-success;
$warning-color: $gap-warning;
$warning-icon-color: $gap-warning;

@if $color-scheme == "dark" {
    $titlebar-color: mix(black, $gap-background, 25%);
    $sidebar-color: mix(black, $gap-background, 8%);
    $input-color: mix($gap-foreground, $gap-surface, 4%);
    $toplevel-border-color: rgba(black, 0.75);
    $border-color: rgba(black, 0.3);
    $insensitive-base-color: rgba(0, 0, 0, 0.075);
}

@function bg-color($level) {
    @return nth(($input-color, $gap-surface, $gap-background, $sidebar-color,
        $titlebar-color), $level + 1);
}

"""
SURFACES_START = "// The default titlebar color"
SURFACES_END = "// Disabled text, images, other foreground elements"

ACCENT = re.compile(r"^@define-color accent_color mix\(.*\);$", re.MULTILINE)
SHADE = re.compile(r"^\$(" + "|".join(RAMPS) + r")_(\d00): #[0-9a-fA-F]+;$", re.M)


def between(text: str, start: str, end: str, replacement: str) -> str:
    head, found, rest = text.partition(start)
    if not found or end not in rest:
        raise SystemExit(f"upstream changed: {start!r} .. {end!r} not found")
    return head + replacement + end + rest.split(end, 1)[1]


def palette(text: str) -> str:
    text, count = SHADE.subn(
        lambda m: f"${m[1]}_{m[2]}: gap-ramp({RAMPS[m[1]]}, {m[2]});", text
    )
    if count != 5 * len(RAMPS):
        raise SystemExit(f"upstream palette changed: {count} role shades")
    return RAMP_FUNCTION + text


def entry(variant: str, version: str) -> str:
    text = variant.replace(
        "@import '../_palette.scss';", f"@import '../sass/{version}/palette';"
    ).replace("@import '../index.scss';", f"@import '../sass/{version}/index';")
    text, count = ACCENT.subn("@define-color accent_color #{$gap-accent};", text)
    if count != 1 or "../sass/" not in text:
        raise SystemExit("upstream variant entry changed")
    return text


def main() -> None:
    upstream = Path(sys.argv[1]).resolve()
    src = upstream / "src"
    commit = subprocess.run(
        ["git", "-C", str(upstream), "log", "-1", "--format=%h %cs"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    shutil.rmtree(PACK, ignore_errors=True)

    for version in VERSIONS:
        sass = PACK / "sass" / version
        shutil.copytree(
            src / version,
            sass,
            ignore=shutil.ignore_patterns("variants", "plank", "assets", "*.build"),
        )
        own = sass / "_palette.scss"
        own.write_text(palette(own.read_text()))
        index = sass / "_index.scss"
        index.write_text(
            between(index.read_text(), SURFACES_START, SURFACES_END, SURFACES)
        )

        (PACK / version).mkdir()
        for variant, suffix in (("light", ""), ("dark", "-dark")):
            text = (src / version / "variants" / f"blueberry{suffix}.scss").read_text()
            (PACK / version / f"gtk-{variant}.scss").write_text(entry(text, version))

        shutil.copytree(
            src / version / "assets", PACK / "files" / "common" / version / "assets"
        )

    label = {
        "label": "elementary",
        "author": "elementary, Inc.",
        "version": commit[1],
        "licence": "GPL-3.0",
        "source": "https://github.com/elementary/stylesheet",
    }
    (PACK / "skin.json").write_text(json.dumps(label, indent=2) + "\n")
    shutil.copy(upstream / "COPYING", PACK / "LICENSE")
    (PACK / "SOURCES.md").write_text(
        f"Made by shell/skins/make_elementary.py from elementary/stylesheet"
        f" {commit[0]} ({commit[1]}),\n{label['source']}, GPL-3.0. The Sass and"
        " pictures are upstream's; the\naccent entries, the role ramps in each"
        " `_palette.scss` and the surfaces in each\n`_index.scss` are Osiris's.\n"
    )
    print("wrote", PACK)


if __name__ == "__main__":
    main()
