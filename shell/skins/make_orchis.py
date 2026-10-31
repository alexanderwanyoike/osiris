"""Make the Orchis skinpack from Orchis's upstream source.

    git clone https://github.com/vinceliuice/Orchis-theme /some/where
    python3 shell/skins/make_orchis.py /some/where

Rewrites shell/skins/orchis/. Run again to follow an upstream release; nothing
here runs when a person wears the Skin (ADR 0019).
"""

import copy
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from makers import Recolour, plank, referenced, replace, revision, rewrite

PACK = Path(__file__).resolve().parent / "orchis"

PALETTE = """\
// Orchis's palette, rebuilt from the Theme's colours ($gap-* from _gaps.scss).
@import 'gaps';

$red-light: $gap-danger;     $red-dark: $gap-danger;
$pink-light: #F06292;        $pink-dark: #EC407A;
$purple-light: #BA68C8;      $purple-dark: #AB47BC;
$blue-light: $gap-accent;    $blue-dark: $gap-accent;
$teal-light: #4DB6AC;        $teal-dark: #009688;
$green-light: #66BB6A;       $green-dark: #4CAF50;
$sea-light: $gap-success;    $sea-dark: $gap-success;
$yellow-light: $gap-warning; $yellow-dark: $gap-warning;
$orange-light: #FB8C00;      $orange-dark: #F57C00;

// Orchis paints windows from background(a..h) in _colors.scss. Light Themes
// use a..d ($white, grey-050, grey-100, grey-250) with the window on grey-100
// and header bars, views and popovers on white; dark Themes use e..h
// (grey-800 to grey-650) with the window on grey-800 and header bars and views
// on grey-700. Those slots are anchored to the Theme's background and surface;
// the rest of the ramp runs towards the foreground.
@function g($if-light, $if-dark) {
  @return if($gap-variant == 'light', $if-light, $if-dark);
}
@function fg($weight, $over: $gap-background) {
  @return mix($gap-foreground, $over, $weight);
}

$white:    g($gap-surface, $gap-foreground);
$grey-050: g(mix($gap-surface, $gap-background, 50%), fg(96%));
$grey-100: g($gap-background, fg(92%));
$grey-150: g(fg(4%), fg(88%));
$grey-200: g(fg(9%), fg(82%));
$grey-250: g(fg(15%), fg(75%));
$grey-300: g(fg(22%), fg(70%));
$grey-350: g(fg(35%), fg(57%));
$grey-400: g(fg(37%), fg(55%));
$grey-450: g(fg(47%), fg(45%));
$grey-500: g(fg(57%), fg(35%));
$grey-550: g(fg(70%), fg(22%));
$grey-600: g(fg(78%), fg(15%));
$grey-650: g(fg(88%), fg(8%, $gap-surface));
$grey-700: g($gap-foreground, $gap-surface);
$grey-750: g(mix(#000, $gap-foreground, 12%), mix($gap-surface, $gap-background, 50%));
$grey-800: g(mix(#000, $gap-foreground, 22%), $gap-background);
$grey-850: g(mix(#000, $gap-foreground, 35%), mix(#000, $gap-background, 20%));
$grey-900: g(mix(#000, $gap-foreground, 45%), mix(#000, $gap-background, 35%));
$grey-950: g(mix(#000, $gap-foreground, 60%), mix(#000, $gap-background, 60%));

$black: #000000;

// Orchis's round window buttons keep their own colours.
$button-close: #fd5f51;
$button-max: #38c76a;
$button-min: #fdbe04;

// Text on a colour is drawn in whichever of the Theme's background and
// foreground is darker (on light colours) or lighter (on dark colours).
$fg-darker: lightness($gap-foreground) < lightness($gap-background);
$ink-dark: if($fg-darker, $gap-foreground, $gap-background);
$ink-light: if($fg-darker, $gap-background, $gap-foreground);

@function osiris-brightness($c) {
  @return (red($c) * 299 + green($c) * 587 + blue($c) * 114) / 1000;
}

$osiris-midpoint: (osiris-brightness($ink-dark) + osiris-brightness($ink-light)) / 2;
"""

# Orchis's on() picks pure black or white text at a fixed brightness; these
# point it at the inks the palette derives from the Theme, split where the
# Theme's own inks split, so a fill gets whichever reads better.
ON_GAPS = (
    ("@if ($brightness >= 156) {", "@if ($brightness >= $osiris-midpoint) {"),
    ("@return rgba(black, 0.87);", "@return $ink-dark;"),
    ("rgba(black, ", "rgba($ink-dark, "),
    ("@return white;", "@return $ink-light;"),
    ("rgba(white, ", "rgba($ink-light, "),
)
PLACEHOLDER = (
    "if($variant == 'light', mix(black, $base, 60%), mix(white, $base, 70%))",
    "if($variant == 'light', mix($ink-dark, $base, 60%), mix($ink-light, $base, 70%))",
)

SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
HREF = f"{{{XLINK}}}href"

# Upstream renders these to PNG per accent (gtk/render-assets.sh). Cut out of
# assets.svg as SVGs instead, their gradients' stops can carry the gaps.
STOP_GAPS = {
    "color-primary-dark": "{{accent}}",
    "color-primary-light": "{{accent}}",
    "color-background": "{{background}}",
    "color-background-dark": "{{background}}",
    "color-surface": "{{surface}}",
    "color-surface-dark": "{{surface}}",
    "color-on-primary-dark": "{{background}}",
    "color-on-primary-light": "{{background}}",
    "color-text-secondary-disabled": "{{foreground}}",
    "color-text-secondary-disabled-dark": "{{foreground}}",
}
# The selected sidebar row's corners are filled with the view colour ($base),
# which is the Theme's surface in both variants.
ROW_GAPS = Recolour(
    {
        "#ffffff": "{{surface}}",
        "#2c2c2c": "{{surface}}",
        "#0f0f0f": "{{surface}}",
    }
)

# The colours Orchis's cinnamon/make-assets.sh swaps, plus the check and radio
# green, which the Sass draws as $success ($check_radio 'default').
CINNAMON_GAPS = Recolour(
    {
        "#1a73e8": "{{accent}}",
        "#3281ea": "{{accent}}",
        "#0f9d58": "{{success}}",
        "#81c995": "{{success}}",
    }
)
CINNAMON_THEMED = ("add-workspace-active", "corner-ripple", "toggle-on")

# Orchis's own default build: the light window uses its light header bar
# (gtk-Light); Cinnamon has no such entry, so its light panel stays dark.
# The dock's fill and badge take the Theme's colours.
DOCK = {
    "FillStartColor": "{{background_plank}}",
    "FillEndColor": "{{background_plank}}",
    "BadgeColor": "{{danger_plank}}",
}
ENTRIES = {
    "gtk-3.0": ("gtk/3.0/gtk-Light.scss", "gtk/3.0/gtk-Dark.scss"),
    "gtk-4.0": ("gtk/4.0/gtk-Light.scss", "gtk/4.0/gtk-Dark.scss"),
    "libadwaita": ("gtk/4.0/gtk-Light.scss", "gtk/4.0/gtk-Dark.scss"),
    "cinnamon": ("cinnamon/cinnamon.scss", "cinnamon/cinnamon-Dark.scss"),
}
STEMS = {
    "gtk-3.0": "gtk",
    "gtk-4.0": "gtk",
    "libadwaita": "libadwaita",
    "cinnamon": "cinnamon",
}


def colours(sass: Path) -> None:
    path = sass / "_colors.scss"
    text = path.read_text()
    start = text.index("@function on(")
    end = text.index("@function highlight(")
    block = text[start:end]
    for old, new in ON_GAPS:
        block = replace(block, old, new, "on()")
    text = text[:start] + block + text[end:]
    path.write_text(replace(text, *PLACEHOLDER, "_colors.scss"))


def svg_assets(gtk: Path, dst: Path) -> None:
    ET.register_namespace("", SVG)
    ET.register_namespace("xlink", XLINK)
    root = ET.parse(gtk / "assets.svg").getroot()
    ids = {el.get("id"): el for el in root.iter() if el.get("id")}
    defs = copy.deepcopy(root.find(f"{{{SVG}}}defs"))
    gradients = {g.get("id") for g in defs.iter(f"{{{SVG}}}linearGradient")}
    if missing := set(STOP_GAPS) - gradients:
        raise SystemExit(f"upstream changed: no {', '.join(sorted(missing))}")
    for gradient in defs.iter(f"{{{SVG}}}linearGradient"):
        gap = STOP_GAPS.get(gradient.get("id", ""))
        if gap is None:
            continue
        for stop in gradient:
            stop.set("stop-color", gap)
            # Upstream dims black check marks to 0.87; the Theme's ink is solid.
            if "on-primary" in gradient.get("id", ""):
                stop.attrib.pop("stop-opacity", None)
    for el in defs.iter():
        for key in [k for k in el.attrib if k.startswith("{") and k != HREF]:
            del el.attrib[key]

    defined = {el.get("id"): el for el in defs.iter() if el.get("id")}

    dst.mkdir(parents=True, exist_ok=True)
    for name in (gtk / "assets.txt").read_text().split():
        group = ids[name]
        x, y, width, height = bounds(group, ids)
        used = referenced(group, defined)
        for suffix, scale in (("", 1), ("@2", 2)):
            svg = ET.Element(
                f"{{{SVG}}}svg",
                {
                    "width": f"{width * scale:g}",
                    "height": f"{height * scale:g}",
                    "viewBox": f"{x:g} {y:g} {width:g} {height:g}",
                },
            )
            if used:
                ET.SubElement(svg, f"{{{SVG}}}defs").extend(
                    copy.deepcopy(defined[i]) for i in used
                )
            svg.append(copy.deepcopy(group))
            text = ROW_GAPS(ET.tostring(svg, encoding="unicode"))
            (dst / f"{name}{suffix}.svg").write_text(text + "\n")


def bounds(group: ET.Element, ids: dict[str, ET.Element]) -> tuple[float, ...]:
    """The box inkscape --export-id renders for one of assets.txt's groups."""
    found = re.match(
        r"translate\(([-\d.e]+)[ ,]+([-\d.e]+)\)", group.get("transform", "")
    )
    tx, ty = (float(found[1]), float(found[2])) if found else (0.0, 0.0)
    first = group[0]
    # Bases are drawn on a transparent box, sometimes through a rotated <use>
    # of another base that keeps the same box.
    while first.tag == f"{{{SVG}}}use":
        first = ids[first.get(HREF, "")[1:]][0]
    x, y = float(first.get("x", 0)), float(first.get("y", 0))
    return tx + x, ty + y, float(first.get("width")), float(first.get("height"))


def svgs(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for svg in src.glob("*.svg"):
        (dst / svg.name).write_text(CINNAMON_GAPS(svg.read_text()))


def make(upstream: Path, pack: Path) -> None:
    src = upstream / "src"
    commit = revision(upstream)

    sass = pack / "sass"
    shutil.copytree(src / "_sass", sass, ignore=shutil.ignore_patterns("gnome-shell"))
    tweaks = (sass / "_tweaks.scss").read_text()
    (sass / "_tweaks-temp.scss").write_text(
        replace(
            tweaks,
            "@import 'color-palette-default';",
            "@import 'color-palette-osiris';",
            "_tweaks.scss",
        )
    )
    (sass / "_color-palette-osiris.scss").write_text(PALETTE)
    colours(sass)
    pictures = 0
    for scss in (sass / "gtk").rglob("*.scss"):
        text, count = re.subn(r"""\.png(['"])""", r".svg\1", scss.read_text())
        scss.write_text(text)
        pictures += count
    if not pictures:
        raise SystemExit("upstream changed: the GTK Sass names no PNG pictures")

    for folder, (light, dark) in ENTRIES.items():
        (pack / folder).mkdir()
        for variant, entry in (("light", light), ("dark", dark)):
            text = (src / entry).read_text()
            text, count = re.subn(r"'(\.\./)+_sass/", "'../sass/", text)
            if not count:
                raise SystemExit(f"upstream changed: {entry} imports no _sass/")
            (pack / folder / f"{STEMS[folder]}-{variant}.scss").write_text(text)

    common = pack / "files" / "common"
    for version in ("gtk-3.0", "gtk-4.0"):
        svg_assets(src / "gtk", common / version / "assets")
        shutil.copytree(
            src / "gtk" / "scalable", common / version / "assets" / "scalable"
        )
    ROW_GAPS.check("assets.svg")
    cinnamon = src / "cinnamon"
    svgs(cinnamon / "common-assets", common / "cinnamon" / "assets")
    for variant, suffix in (("light", ""), ("dark", "-Dark")):
        dst = pack / "files" / variant / "cinnamon" / "assets"
        svgs(cinnamon / f"assets{suffix}", dst)
        for name in CINNAMON_THEMED:
            svg = cinnamon / "theme" / f"{name}{suffix}.svg"
            (dst / f"{name}.svg").write_text(CINNAMON_GAPS(svg.read_text()))
    CINNAMON_GAPS.check("the Cinnamon pictures")

    (pack / "plank").mkdir()
    dock = plank(src / "plank" / "dock.theme", DOCK)
    for variant in ("light", "dark"):
        (pack / "plank" / f"dock-{variant}.theme").write_text(dock)

    label = {
        "label": "Orchis",
        "author": "Vince Liuice",
        "version": commit[1],
        "licence": "GPL-3.0",
        "source": "https://github.com/vinceliuice/Orchis-theme",
    }
    (pack / "skin.json").write_text(json.dumps(label, indent=2) + "\n")
    shutil.copy(upstream / "COPYING", pack / "LICENSE")
    (pack / "SOURCES.md").write_text(
        f"Made by shell/skins/make_orchis.py from Orchis-theme {commit[0]}"
        f" ({commit[1]}),\n{label['source']}, GPL-3.0. The Sass and pictures are"
        " upstream's; the\npalette (`sass/_color-palette-osiris.scss`), the text"
        " colours in\n`sass/_colors.scss`, the SVGs cut from `src/gtk/assets.svg`"
        " in place of its\nPNGs, and the gap markers are Osiris's.\n"
    )


def main() -> None:
    upstream = Path(sys.argv[1]).resolve()
    rewrite(PACK, lambda pack: make(upstream, pack))
    print("wrote", PACK)


if __name__ == "__main__":
    main()
