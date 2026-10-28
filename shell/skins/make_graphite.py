"""Make the Graphite skinpack from Graphite's upstream source.

    git clone https://github.com/vinceliuice/Graphite-gtk-theme /some/where
    python3 shell/skins/make_graphite.py /some/where

Rewrites shell/skins/graphite/. Run again to follow an upstream release; nothing
here runs when a person wears the Skin (ADR 0019).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from makers import Recolour, replace, replace_once

PACK = Path(__file__).resolve().parent / "graphite"

# Graphite keeps its colours in functions inside _colors.scss rather than in a
# palette file, so this is imported between those functions and their first
# use: a later @function replaces an earlier one.
PALETTE = """\
// Graphite's colours, rebuilt from the Theme's colours ($gap-* from _gaps.scss).
@import 'gaps';

$osiris-light: $gap-variant == 'light';
$osiris-dark-ink: if($osiris-light, $gap-foreground, $gap-background);
$osiris-light-ink: if($osiris-light, $gap-background, $gap-foreground);

@function osiris-brightness($c) {
  @return (red($c) * 299 + green($c) * 587 + blue($c) * 114) / 1000;
}

$osiris-midpoint: (
  osiris-brightness($gap-foreground) + osiris-brightness($gap-background)
) / 2;

// Graphite is monochrome: its theme colour is its only accent.
@function theme($color) {
  @return $gap-accent;
}

// Upstream's two grey ramps: a-d the light end, e-h the dark end. The end on
// the Theme's side is anchored to its background and surface; the far end
// (Graphite's dark tooltips on a light window) comes from its foreground.
$osiris-ramp: if($osiris-light, (
  a: $gap-background,
  b: $gap-surface,
  c: $gap-surface,
  d: mix($gap-foreground, $gap-background, 25%),
  e: mix(#000, $gap-foreground, 10%),
  f: mix(#000, $gap-foreground, 5%),
  g: $gap-foreground,
  h: mix($gap-background, $gap-foreground, 10%),
), (
  a: $gap-foreground,
  b: mix($gap-background, $gap-foreground, 3%),
  c: mix($gap-background, $gap-foreground, 6%),
  d: mix($gap-background, $gap-foreground, 25%),
  e: $gap-surface,
  f: $gap-surface,
  g: $gap-background,
  h: mix($gap-foreground, $gap-surface, 9%),
));

@function background($type) {
  @return map-get($osiris-ramp, $type);
}

// Upstream inks in black or white; these ink in the Theme's foreground and
// background, keeping upstream's opacity for each state.
$osiris-on-light: (primary: 1, secondary: 0.6, disabled: 0.38, secondary-disabled: 0.26,
  track: 0.26, track-disabled: 0.12, divider: 0.12, secondary-fill: 0.08, fill: 0.04);
$osiris-on-dark: (primary: 1, secondary: 0.7, disabled: 0.5, secondary-disabled: 0.3,
  track: 0.3, track-disabled: 0.12, divider: 0.12, secondary-fill: 0.08, fill: 0.04);

@function on($color, $state: 'primary') {
  @if ($color == 'light') { $color: $osiris-light-ink; }
  @if ($color == 'dark') { $color: $osiris-dark-ink; }

  @if (osiris-brightness($color) >= $osiris-midpoint) {
    @return rgba($osiris-dark-ink, map-get($osiris-on-light, $state));
  }
  @return rgba($osiris-light-ink, map-get($osiris-on-dark, $state));
}
"""

# _colors.scss sets these as literals after its functions run, so they are
# replaced from the end of the file.
COLORS = """\
// Graphite's fixed colours, taken from the Theme.
$warning: $gap-warning;
$error: $gap-danger;
$destructive: $gap-danger;
$success: $gap-success;
$link: $gap-accent;

// Graphite's styled sidebar keeps its shape; the Theme's surface colours it.
$sidebg: $gap-surface;
"""

COLORS_ANCHOR = "//\n// Basic colors\n"
# Upstream treats a theme colour of 'default' as grey and swaps in grey-only
# pictures and paths; ours is the Theme's accent, so it must read as a colour.
THEME_TWEAK = ("$theme: 'default';", "$theme: 'osiris';")

# Graphite ships one folder of pictures per accent instead of recolouring them;
# the blue one's accent and the off-state ink become gaps.
CINNAMON_ACCENT = Recolour({"#3684dd": "{{accent}}"})
CINNAMON_INK = {
    "light": Recolour({"#333333": "{{foreground}}"}),
    "dark": Recolour({"#dfdfdf": "{{foreground}}"}),
}

ENTRIES = {
    "gtk-3.0/gtk": "gtk-3.0/gtk",
    "gtk-4.0/gtk": "gtk-4.0/gtk",
    "cinnamon/cinnamon": "cinnamon/cinnamon",
    # Upstream themes libadwaita by linking its GTK 4 sheet as the user sheet.
    "libadwaita/libadwaita": "gtk-4.0/gtk",
}


def svgs(src: Path, dst: Path, recolour: Recolour | None = None) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for svg in src.glob("*.svg"):
        text = svg.read_text()
        (dst / svg.name).write_text(recolour(text) if recolour else text)


def plank(src: Path) -> str:
    fills = ("FillStartColor", "FillEndColor")
    lines = src.read_text().splitlines()
    return (
        "\n".join(
            f"{line.split('=')[0]}={{{{surface_plank}}}}"
            if line.startswith(fills)
            else line
            for line in lines
        )
        + "\n"
    )


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

    sass = PACK / "sass"
    shutil.copytree(src / "sass", sass, ignore=shutil.ignore_patterns("gnome-shell"))
    tweaks = (src / "sass" / "_tweaks.scss").read_text()
    (sass / "_tweaks-temp.scss").write_text(
        replace_once(tweaks, *THEME_TWEAK, "_tweaks.scss")
    )
    colors = replace_once(
        (sass / "_colors.scss").read_text(),
        COLORS_ANCHOR,
        "@import 'color-palette-osiris';\n\n" + COLORS_ANCHOR,
        "_colors.scss",
    )
    (sass / "_colors.scss").write_text(colors + "\n@import 'colors-osiris';\n")
    (sass / "_color-palette-osiris.scss").write_text(PALETTE)
    (sass / "_colors-osiris.scss").write_text(COLORS)
    for entry, source in ENTRIES.items():
        (PACK / entry).parent.mkdir(exist_ok=True)
        for variant in ("Light", "Dark"):
            text = (src / "main" / f"{source}-{variant}.scss").read_text()
            out = PACK / f"{entry}-{variant.lower()}.scss"
            out.write_text(replace(text, "'../../sass/", "'../sass/", out.name))

    common = PACK / "files" / "common"
    gtk = src / "assets" / "gtk"
    for version in ("gtk-3.0", "gtk-4.0"):
        shutil.copytree(gtk / "assets", common / version / "assets")
        svgs(gtk / "scalable", common / version / "assets" / "scalable")
    cinnamon = src / "assets" / "cinnamon"
    svgs(cinnamon / "common-assets", common / "cinnamon" / "assets")
    svgs(cinnamon / "theme-blue", common / "cinnamon" / "assets", CINNAMON_ACCENT)
    for variant, folder in (("light", "assets"), ("dark", "assets-Dark")):
        dst = PACK / "files" / variant / "cinnamon" / "assets"
        svgs(cinnamon / folder, dst, CINNAMON_INK[variant])
    CINNAMON_ACCENT.check("cinnamon/theme-blue")
    for variant, recolour in CINNAMON_INK.items():
        recolour.check(f"cinnamon {variant} pictures")

    (PACK / "plank").mkdir()
    for variant in ("Light", "Dark"):
        dock = plank(src / "main" / "plank" / f"theme-{variant}" / "dock.theme")
        (PACK / "plank" / f"dock-{variant.lower()}.theme").write_text(dock)

    label = {
        "label": "Graphite",
        "author": "Vince Liuice",
        "version": commit[1],
        "licence": "GPL-3.0",
        "source": "https://github.com/vinceliuice/Graphite-gtk-theme",
    }
    (PACK / "skin.json").write_text(json.dumps(label, indent=2) + "\n")
    shutil.copy(upstream / "LICENSE", PACK / "LICENSE")
    (PACK / "SOURCES.md").write_text(
        f"Made by shell/skins/make_graphite.py from Graphite-gtk-theme {commit[0]}"
        f" ({commit[1]}),\n{label['source']}, GPL-3.0. The Sass and pictures are"
        " upstream's; the\npalette (`sass/_color-palette-osiris.scss`,"
        " `sass/_colors-osiris.scss`), the two\nimports of them in"
        " `sass/_colors.scss` and the gap markers are Osiris's.\n"
    )
    print("wrote", PACK)


if __name__ == "__main__":
    main()
