"""Make the Jasper skinpack from Jasper's upstream source.

    git clone https://github.com/vinceliuice/Jasper-gtk-theme /some/where
    python3 shell/skins/make_jasper.py /some/where

Rewrites shell/skins/jasper/. Run again to follow an upstream release; nothing
here runs when a person wears the Skin (ADR 0019).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from makers import Recolour, replace

PACK = Path(__file__).resolve().parent / "jasper"

PALETTE = """\
// Jasper's palette, rebuilt from the Theme's colours ($gap-* from _gaps.scss).
@import 'gaps';

$red-light: $gap-danger;     $red-dark: $gap-danger;
$pink-light: #F06292;        $pink-dark: #EC407A;
$purple-light: #BA68C8;      $purple-dark: #AB47BC;
$blue-light: $gap-accent;    $blue-dark: $gap-accent;
$teal-light: $gap-accent;    $teal-dark: $gap-accent;
$green-light: $gap-success;  $green-dark: $gap-success;
$yellow-light: $gap-warning; $yellow-dark: $gap-warning;
$orange-light: #FF8A65;      $orange-dark: #FF7043;

// Jasper picks its surfaces from this grey ramp: light Themes use its light
// end (grey-100 window and header bar, white views), dark Themes its dark end
// (grey-800 window, grey-750 header bar, grey-700 views, grey-650 cards).
// Each end is anchored to the Theme; the weights keep upstream's spacing.
$light: $gap-variant == 'light';
@function ramp($weight) {
  @return mix($gap-foreground, $gap-background, $weight);
}
@function g($light-weight, $dark-weight) {
  @return ramp(if($light, $light-weight, $dark-weight));
}

$grey-050: if($light, mix($gap-surface, $gap-background, 50%), ramp(98%));
$grey-100: g(0%,   94%);
$grey-150: g(2%,   92%);
$grey-200: g(10%,  85%);
$grey-250: g(18%,  77%);
$grey-300: g(24%,  71%);
$grey-350: g(39%,  57%);
$grey-400: g(40%,  56%);
$grey-450: g(52%,  45%);
$grey-500: g(61%,  36%);
$grey-550: g(75%,  23%);
$grey-600: g(82%,  17%);
$grey-650: if($light, ramp(87%), mix($gap-foreground, $gap-surface, 12%));
$grey-700: if($light, ramp(95%), mix($gap-foreground, $gap-surface, 5%));
$grey-750: if($light, ramp(98%), $gap-surface);
$grey-800: if($light, $gap-foreground, $gap-background);
$grey-850: mix(#000, $grey-800, 25%);
$grey-900: mix(#000, $grey-800, 35%);
$grey-950: mix(#000, $grey-800, 60%);

// Jasper's on() draws text in $white or $black, so these carry the Theme's
// foreground; in light Themes $white is also the view colour.
$white: if($light, $gap-surface, $gap-foreground);
$black: if($light, $gap-foreground, #000000);

// on() switches between them where their brightness splits, as Graphite does,
// so each fill gets whichever reads better.
@function osiris-brightness($c) {
  @return (red($c) * 299 + green($c) * 587 + blue($c) * 114) / 1000;
}

$osiris-midpoint: (osiris-brightness($white) + osiris-brightness($black)) / 2;

// Jasper's window buttons keep their own colours.
$button-close: #fd5f51;
$button-max: #38c76a;
$button-min: #fdbe04;

$default-light: $gap-accent;
$default-dark: $gap-accent;
"""

# The accent Jasper's own scripts swap in its Cinnamon pictures
# (src/assets/cinnamon/make-assets.sh), and its dark knob and tick grey.
SVG_GAPS = Recolour({
    "#009688": "{{accent}}",
    "#4db6ac": "{{accent}}",
    "#242424": "{{background}}",
})
# Jasper's on() switches to dark text at a fixed brightness.
THRESHOLD = ("@if ($brightness >= 156) {", "@if ($brightness >= $osiris-midpoint) {")
ENTRIES = {
    "gtk-3.0/gtk": "gtk-3.0/gtk",
    "gtk-4.0/gtk": "gtk-4.0/gtk",
    "cinnamon/cinnamon": "cinnamon/cinnamon",
    # Upstream has no libadwaita sheet: `install.sh -l` links its gtk-4.0 sheet
    # into ~/.config/gtk-4.0, so the same entry serves libadwaita.
    "libadwaita/libadwaita": "gtk-4.0/gtk",
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
    for entry, source in ENTRIES.items():
        (PACK / entry).parent.mkdir()
        for variant in ("Light", "Dark"):
            text = (src / "main" / f"{source}-{variant}.scss").read_text()
            out = PACK / f"{entry}-{variant.lower()}.scss"
            out.write_text(replace(text, "'../../sass/", "'../sass/", out.name))

    common = PACK / "files" / "common"
    gtk = src / "assets" / "gtk"
    for version in ("gtk-3.0", "gtk-4.0"):
        # Upstream renders these PNGs in its default accent; sassc cannot
        # re-render them, so they keep that colour.
        shutil.copytree(gtk / "assets", common / version / "assets")
        svgs(gtk / "scalable", common / version / "assets" / "scalable", False)
    cinnamon = src / "assets" / "cinnamon"
    svgs(cinnamon / "common-assets", common / "cinnamon" / "assets", False)
    svgs(cinnamon / "theme", common / "cinnamon" / "assets")
    for variant, folder in (("light", "assets"), ("dark", "assets-Dark")):
        dst = PACK / "files" / variant / "cinnamon" / "assets"
        svgs(cinnamon / folder, dst)
    SVG_GAPS.check("the pictures")

    (PACK / "plank").mkdir()
    for variant in ("Light", "Dark"):
        dock = plank(src / "main" / "plank" / f"theme-{variant}" / "dock.theme")
        (PACK / "plank" / f"dock-{variant.lower()}.theme").write_text(dock)

    label = {
        "label": "Jasper",
        "author": "Vince Liuice",
        "version": commit[1],
        "licence": "GPL-3.0",
        "source": "https://github.com/vinceliuice/Jasper-gtk-theme",
    }
    (PACK / "skin.json").write_text(json.dumps(label, indent=2) + "\n")
    shutil.copy(upstream / "LICENSE", PACK / "LICENSE")
    (PACK / "SOURCES.md").write_text(
        f"Made by shell/skins/make_jasper.py from Jasper-gtk-theme {commit[0]}"
        f" ({commit[1]}),\n{label['source']}, GPL-3.0. The Sass and pictures are"
        " upstream's; the\npalette (`sass/_color-palette-osiris.scss`) and the"
        " gap markers are Osiris's.\n"
    )
    print("wrote", PACK)


if __name__ == "__main__":
    main()
