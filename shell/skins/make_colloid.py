"""Make the Colloid skinpack from Colloid's upstream source.

    git clone https://github.com/vinceliuice/Colloid-gtk-theme /some/where
    python3 shell/skins/make_colloid.py /some/where

Rewrites shell/skins/colloid/. Run again to follow an upstream release; nothing
here runs when a person wears the Skin (ADR 0019).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from makers import Recolour, replace

PACK = Path(__file__).resolve().parent / "colloid"

PALETTE = """\
// Colloid's palette, rebuilt from the Theme's colours ($gap-* from _gaps.scss).
@import 'gaps';

$red-light: $gap-danger;     $red-dark: $gap-danger;
$pink-light: #F06292;        $pink-dark: #EC407A;
$purple-light: #BA68C8;      $purple-dark: #AB47BC;
$blue-light: $gap-accent;    $blue-dark: $gap-accent;
$teal-light: #4DB6AC;        $teal-dark: #009688;
$green-light: $gap-success;  $green-dark: $gap-success;
$yellow-light: $gap-warning; $yellow-dark: $gap-warning;
$orange-light: #FF8A65;      $orange-dark: #FF7043;

// Colloid draws its surfaces from this grey ramp: light Themes use its light
// end, dark Themes its dark end, so each end is anchored to the Theme.
$light: $gap-variant == 'light';
@function g($light-weight, $dark) {
  @return if($light, mix($gap-foreground, $gap-background, $light-weight), $dark);
}

$grey-050: g(3%,  mix($gap-foreground, $gap-background, 90%));
$grey-100: g(6%,  mix($gap-foreground, $gap-background, 85%));
$grey-150: g(8%,  mix($gap-foreground, $gap-background, 80%));
$grey-200: g(13%, mix($gap-foreground, $gap-background, 72%));
$grey-250: g(20%, mix($gap-foreground, $gap-background, 65%));
$grey-300: g(25%, mix($gap-foreground, $gap-background, 58%));
$grey-350: g(37%, mix($gap-foreground, $gap-background, 48%));
$grey-400: g(38%, mix($gap-foreground, $gap-background, 46%));
$grey-450: g(47%, mix($gap-foreground, $gap-background, 38%));
$grey-500: g(55%, mix($gap-foreground, $gap-background, 30%));
$grey-550: g(67%, mix($gap-foreground, $gap-background, 20%));
$grey-600: g(72%, mix($gap-foreground, $gap-background, 12%));
$grey-650: g(75%, $gap-surface);
$grey-700: g(85%, $gap-background);
$grey-750: g(90%, mix(#000, $gap-background, 12%));
$grey-800: g(94%, mix(#000, $gap-background, 20%));
$grey-850: g(97%, mix(#000, $gap-background, 35%));
$grey-900: g(100%, mix(#000, $gap-background, 45%));
$grey-950: if($light, mix(#000, $gap-foreground, 30%), mix(#000, $gap-background, 70%));

$white: if($light, $gap-background, #FFFFFF);
$black: #000000;

// on() switches between them where their brightness splits, as Graphite does,
// so each fill gets whichever reads better.
@function osiris-brightness($c) {
  @return (red($c) * 299 + green($c) * 587 + blue($c) * 114) / 1000;
}

$osiris-midpoint: (osiris-brightness($white) + osiris-brightness($black)) / 2;

// Colloid's round window buttons keep their own colours.
$button-close: #fd5f51;
$button-max: #38c76a;
$button-min: #fdbe04;

$links: $gap-accent;
$default-light: $gap-accent;
$default-dark: $gap-accent;
"""

# Colloid's on() switches to dark text at a fixed brightness.
THRESHOLD = ("@if ($brightness >= 156) {", "@if ($brightness >= $osiris-midpoint) {")

# Colloid ships no launcher theme; this one follows its rounded, flat panels.
# Its placeholder is the foreground at 60%, the opacity Colloid gives
# secondary text (rofi reads #rrggbbaa).
LAUNCHER = """\
/* Colloid, in the Theme's colours. Made by shell/skins/make_colloid.py. */
* {
    bg:     {{background}};
    panel:  {{surface}};
    fg:     {{foreground}};
    accent: {{accent}};
    font:   "Sans 11";
}
window { transparency: "real"; background-color: @bg; border: 0px;
    border-radius: 12px; width: 600px; padding: 12px; }
mainbox { background-color: transparent; children: [ inputbar, listview ];
    spacing: 10px; }
inputbar { background-color: @panel; border-radius: 999px; padding: 10px 16px;
    spacing: 10px; children: [ prompt, entry ]; }
prompt { background-color: transparent; text-color: @accent; }
entry { background-color: transparent; text-color: @fg; placeholder: "Search";
    placeholder-color: {{foreground}}99; }
listview { background-color: transparent; lines: 8; scrollbar: false;
    spacing: 4px; fixed-height: false; }
element { background-color: transparent; text-color: @fg; border-radius: 8px;
    padding: 8px 12px; spacing: 10px; children: [ element-icon, element-text ]; }
element-icon { background-color: transparent; size: 22px; vertical-align: 0.5; }
element-text { background-color: transparent; text-color: inherit;
    vertical-align: 0.5; }
element selected { background-color: @accent; text-color: @bg; }
"""

# The colours Colloid's own installer swaps in its pictures (assets.sh).
SVG_GAPS = Recolour({
    "#5b9bf8": "{{accent}}",
    "#3c84f7": "{{accent}}",
    "#ffffff": "{{background}}",
    "#2c2c2c": "{{background}}",
    "#3c3c3c": "{{surface}}",
})
ENTRIES = {
    "gtk-3.0": "gtk",
    "gtk-4.0": "gtk",
    "cinnamon": "cinnamon",
    "libadwaita": "libadwaita",
}


def svgs(src: Path, dst: Path, gaps: bool = True) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for svg in src.glob("*.svg"):
        text = svg.read_text()
        (dst / svg.name).write_text(SVG_GAPS(text) if gaps else text)


def plank(src: Path) -> str:
    fills = ("FillStartColor", "FillEndColor", "InnerStrokeColor")
    lines = src.read_text().splitlines()
    return (
        "\n".join(
            f"{line.split('=')[0]}={{{{background_plank}}}}"
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

    shutil.copytree(
        src / "sass", PACK / "sass", ignore=shutil.ignore_patterns("gnome-shell")
    )
    tweaks = (src / "sass" / "_tweaks.scss").read_text()
    (PACK / "sass" / "_tweaks-temp.scss").write_text(
        replace(
            tweaks,
            "@import 'color-palette-default';",
            "@import 'color-palette-osiris';",
            "_tweaks.scss",
        )
    )
    (PACK / "sass" / "_color-palette-osiris.scss").write_text(PALETTE)
    colors = PACK / "sass" / "_colors.scss"
    colors.write_text(replace(colors.read_text(), *THRESHOLD, "_colors.scss"))
    for folder, stem in ENTRIES.items():
        (PACK / folder).mkdir()
        for variant in ("Light", "Dark"):
            text = (src / "main" / folder / f"{stem}-{variant}.scss").read_text()
            out = PACK / folder / f"{stem}-{variant.lower()}.scss"
            out.write_text(replace(text, "'../../sass/", "'../sass/", out.name))

    common = PACK / "files" / "common"
    for version in ("gtk-3.0", "gtk-4.0"):
        svgs(src / "assets" / "gtk" / "assets", common / version / "assets")
        svgs(src / "assets" / "gtk" / "symbolics", common / version / "assets", False)
    cinnamon = src / "assets" / "cinnamon"
    svgs(cinnamon / "theme", common / "cinnamon" / "assets")
    svgs(cinnamon / "common-assets", common / "cinnamon" / "assets", False)
    for variant, folder in (("light", "assets"), ("dark", "assets-Dark")):
        dst = PACK / "files" / variant / "cinnamon" / "assets"
        svgs(cinnamon / folder, dst, False)
    SVG_GAPS.check("the pictures")

    (PACK / "plank").mkdir()
    for variant in ("Light", "Dark"):
        dock = plank(src / "main" / "plank" / f"theme-{variant}" / "dock.theme")
        (PACK / "plank" / f"dock-{variant.lower()}.theme").write_text(dock)

    (PACK / "rofi").mkdir()
    (PACK / "rofi" / "launcher.rasi").write_text(LAUNCHER)

    label = {
        "label": "Colloid",
        "author": "Vince Liuice",
        "version": commit[1],
        "licence": "GPL-3.0",
        "source": "https://github.com/vinceliuice/Colloid-gtk-theme",
    }
    (PACK / "skin.json").write_text(json.dumps(label, indent=2) + "\n")
    shutil.copy(upstream / "LICENSE", PACK / "LICENSE")
    (PACK / "SOURCES.md").write_text(
        f"Made by shell/skins/make_colloid.py from Colloid-gtk-theme {commit[0]}"
        f" ({commit[1]}),\n{label['source']}, GPL-3.0. The Sass and pictures are"
        " upstream's; the\npalette (`sass/_color-palette-osiris.scss`) and the"
        " gap markers are Osiris's.\n"
    )
    print("wrote", PACK)


if __name__ == "__main__":
    main()
