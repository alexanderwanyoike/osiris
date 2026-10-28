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

from makers import replace, replace_once, rewrite

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

// Upstream writes white on its fills; this is whichever of the Theme's inks
// has the higher WCAG contrast. Sass has no pow(), so the 2.4 power of the
// sRGB curve is x^2 times the fifth root of x^2, found by Newton's method.
@function osiris-root5($a) {
    $y: 1;
    @for $i from 1 through 24 {
        $y: (4 * $y + $a / ($y * $y * $y * $y)) / 5;
    }
    @return $y;
}

@function osiris-linear($channel) {
    $c: $channel / 255;
    @if $c <= 0.03928 {
        @return $c / 12.92;
    }
    $t: ($c + 0.055) / 1.055;
    @return $t * $t * osiris-root5($t * $t);
}

@function osiris-luminance($c) {
    @return 0.2126 * osiris-linear(red($c)) + 0.7152 * osiris-linear(green($c))
        + 0.0722 * osiris-linear(blue($c));
}

@function osiris-contrast($a, $b) {
    $la: osiris-luminance($a) + 0.05;
    $lb: osiris-luminance($b) + 0.05;
    @return max($la, $lb) / min($la, $lb);
}

@function osiris-on($fill) {
    $foreground: osiris-contrast($fill, $gap-foreground);
    @if $foreground >= osiris-contrast($fill, $gap-background) {
        @return $gap-foreground;
    }
    @return $gap-background;
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
# The white text upstream puts on the accent and on its danger red.
ON_FILLS = {
    "widgets/_checkbuttons.scss": (
        "background-color: #{'@accent_color'};\n        color: white;",
        "background-color: #{'@accent_color'};\n        color: osiris-on($gap-accent);",
    ),
    "widgets/_buttons.scss": (
        "background-color: $STRAWBERRY_500;\n            color: white;",
        "background-color: $STRAWBERRY_500;\n"
        "            color: osiris-on($STRAWBERRY_500);",
    ),
}

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
    for theirs, ours in (("_palette", "palette"), ("index", "index")):
        old = f"@import '../{theirs}.scss';"
        new = f"@import '../sass/{version}/{ours}';"
        variant = replace(variant, old, new, "a variant entry")
    text, count = ACCENT.subn("@define-color accent_color #{$gap-accent};", variant)
    if count != 1:
        raise SystemExit("upstream variant entry changed")
    return text


def make(upstream: Path, pack: Path) -> None:
    src = upstream / "src"
    commit = subprocess.run(
        ["git", "-C", str(upstream), "log", "-1", "--format=%h %cs"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()

    for version in VERSIONS:
        sass = pack / "sass" / version
        shutil.copytree(
            src / version,
            sass,
            ignore=shutil.ignore_patterns("variants", "plank", "assets", "*.build"),
        )
        own = sass / "_palette.scss"
        own.write_text(palette(own.read_text()))
        for partial, (old, new) in ON_FILLS.items():
            path = sass / partial
            path.write_text(replace_once(path.read_text(), old, new, partial))
        index = sass / "_index.scss"
        index.write_text(
            between(index.read_text(), SURFACES_START, SURFACES_END, SURFACES)
        )

        (pack / version).mkdir()
        for variant, suffix in (("light", ""), ("dark", "-dark")):
            text = (src / version / "variants" / f"blueberry{suffix}.scss").read_text()
            (pack / version / f"gtk-{variant}.scss").write_text(entry(text, version))

        shutil.copytree(
            src / version / "assets", pack / "files" / "common" / version / "assets"
        )

    label = {
        "label": "elementary",
        "author": "elementary, Inc.",
        "version": commit[1],
        "licence": "GPL-3.0",
        "source": "https://github.com/elementary/stylesheet",
    }
    (pack / "skin.json").write_text(json.dumps(label, indent=2) + "\n")
    shutil.copy(upstream / "COPYING", pack / "LICENSE")
    (pack / "SOURCES.md").write_text(
        f"Made by shell/skins/make_elementary.py from elementary/stylesheet"
        f" {commit[0]} ({commit[1]}),\n{label['source']}, GPL-3.0. The Sass and"
        " pictures are upstream's; the\naccent entries, the role ramps and text"
        " inks in each `_palette.scss`, the\nsurfaces in each `_index.scss` and"
        " the inks on checks and destructive buttons\nare Osiris's.\n"
    )


def main() -> None:
    upstream = Path(sys.argv[1]).resolve()
    rewrite(PACK, lambda pack: make(upstream, pack))
    print("wrote", PACK)


if __name__ == "__main__":
    main()
