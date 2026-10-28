"""Make the Qogir skinpack from Qogir's upstream source.

    git clone https://github.com/vinceliuice/Qogir-theme /some/where
    python3 shell/skins/make_qogir.py /some/where

Rewrites shell/skins/qogir/. Run again to follow an upstream release; nothing
here runs when a person wears the Skin (ADR 0019).
"""

import copy
import json
import math
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

PACK = Path(__file__).resolve().parent / "qogir"

PALETTE = """\
// Qogir's palette, rebuilt from the Theme's colours ($gap-* from _gaps.scss).
// _colors.scss derives everything else from these, as it does upstream.
@import 'gaps';

$_light: $variant == 'light';
$_light_with_dark_titlebar: $_light and $titlebar == 'dark';

@function osiris-brightness($c) {
  @return (red($c) * 299 + green($c) * 587 + blue($c) * 114) / 1000;
}

// Whichever of the Theme's inks reads better on $fill, split where the inks
// themselves split, as Graphite does.
@function readable-on($fill) {
  $dark-end: if($_light, $gap-foreground, $gap-background);
  $light-end: if($_light, $gap-background, $gap-foreground);
  $midpoint: (osiris-brightness($dark-end) + osiris-brightness($light-end)) / 2;
  @return if(osiris-brightness($fill) >= $midpoint, $dark-end, $light-end);
}

$base_color: if($_light, mix(#ffffff, $gap-background, 50%),
                 mix(#000000, $gap-background, 12%));
$text_color: $gap-foreground;
$bg_color: $gap-background;
$fg_color: $gap-foreground;

$selected_bg_color: $gap-accent;
$selected_fg_color: readable-on($gap-accent);

$warning_color: $gap-warning;
$error_color: $gap-danger;
$warning_fg_color: readable-on($gap-warning);
$error_fg_color: readable-on($gap-danger);
$success_color: $gap-success;
$destructive_color: $gap-danger;
$destructive_fg_color: readable-on($gap-danger);
$suggested_fg_color: $selected_fg_color;
$drop_target_color: $gap-warning;

// Qogir keeps its panel, OSDs and dark title bars dark on light Themes too;
// there they take the Theme's foreground, darkened, as its dark tone.
$osd_bg_color: if($_light, mix(#000000, $gap-foreground, 35%), $gap-surface);
$osd_fg_color: if($_light, $gap-background, $gap-foreground);
$panel_bg: mix(#000000, $osd_bg_color, 15%);

$_header: if($_light_with_dark_titlebar, $osd_bg_color, $gap-surface);
$header_bg: if($trans == 'true', rgba($_header, 0.95), $_header);
$header_fg: if($_light_with_dark_titlebar, $osd_fg_color, $gap-foreground);

$dark_sidebar_bg: $header_bg;
$dark_sidebar_fg: $header_fg;
$dark_sidebar_icon_bg: $osd_bg_color;
$dark_sidebar_icon_fg: $osd_fg_color;

$_wm_fg: if($_light_with_dark_titlebar, $osd_fg_color, $gap-foreground);
$_light_header: $_light and not $_light_with_dark_titlebar;
$wm_button_hover_bg: if($_light_header, mix(#ffffff, $_header, 50%),
                         mix($_wm_fg, $_header, 16%));
$wm_button_hover_border: if($_light_header, mix($_wm_fg, $_header, 20%),
                             mix(#000000, $_header, 10%));
$wm_icon_bg: mix($_wm_fg, $_header, 60%);
$wm_icon_unfocused_bg: mix($_wm_fg, $_header, 35%);
$wm_icon_hover_bg: mix($_wm_fg, $_header, 80%);
"""

# The names the palette defines, cut from upstream's _colors.scss so its stand.
ROOTS = re.findall(r"^\$([a-z]\w*):", PALETTE, re.MULTILINE)
SVG_NS = "http://www.w3.org/2000/svg"
XLINK = "{http://www.w3.org/1999/xlink}href"

# The colours Qogir's per-accent pictures differ by (assets-Manjaro.svg and
# assets-Ubuntu.svg swap only this one), and the Cinnamon pictures' own.
GTK_GAPS = {"#5294e2": "{{accent}}"}
CINNAMON_GAPS = {
    "#5294e2": "{{accent}}",
    "#4080fb": "{{accent}}",
    "#1d78df": "{{accent}}",
    "#398cd3": "{{accent}}",
    "#398dd3": "{{accent}}",
    "#fcfdfd": "{{background}}",
    "#f5f6f7": "{{background}}",
    "#32343d": "{{background}}",
    "#2d323d": "{{background}}",
    "#323644": "{{background}}",
}
# White is also Qogir's tick and knob colour, so it becomes a gap only where it
# is the menu or box behind them.
CINNAMON_WHITE = ("menu/menu.svg", "checkbox/checkbox-unchecked")
ENTRIES = {
    "gtk-3.0": ("gtk/theme-3.0", "gtk-Light", "gtk-Dark"),
    "gtk-4.0": ("gtk/theme-4.0", "gtk-Light", "gtk-Dark"),
    # Upstream's installer links its GTK 4 sheet into ~/.config/gtk-4.0.
    "libadwaita": ("gtk/theme-4.0", "gtk-Light", "gtk-Dark"),
    "cinnamon": ("cinnamon", "cinnamon", "cinnamon-Dark"),
}


def gapped(text: str, gaps: dict[str, str]) -> str:
    for colour, gap in gaps.items():
        text = re.sub(re.escape(colour), gap, text, flags=re.IGNORECASE)
    return text


def colours(upstream: str) -> str:
    """Upstream's _colors.scss with the palette's names left to the palette."""
    names = "|".join(ROOTS)
    definition = re.compile(rf"^\s*(@if [^{{]*\{{\s*)?\$({names}):")
    lines = upstream.splitlines()
    kept = [line for line in lines if not definition.match(line)]
    found = {definition.match(line)[2] for line in lines if definition.match(line)}
    missing = set(ROOTS) - found
    if missing:
        raise SystemExit(f"_colors.scss no longer defines {', '.join(sorted(missing))}")
    return "\n".join(kept) + "\n"


# Upstream renders its GTK pictures to PNG with Inkscape, one colour per file.
# Cutting each one out of its sheet as an SVG instead lets the Theme fill it.


def matrix(transform: str | None) -> tuple[float, ...]:
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", transform or ""):
        v = [
            float(n)
            for n in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?", args)
        ]
        if name == "matrix":
            step = tuple(v)
        elif name == "translate":
            step = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            step = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate":
            cos, sin = math.cos(math.radians(v[0])), math.sin(math.radians(v[0]))
            cx, cy = (v[1], v[2]) if len(v) > 2 else (0.0, 0.0)
            step = (
                cos,
                sin,
                -sin,
                cos,
                cx - cos * cx + sin * cy,
                cy - sin * cx - cos * cy,
            )
        else:
            raise SystemExit(f"unhandled SVG transform {name}")
        m = compose(m, step)
    return m


def compose(m: tuple[float, ...], n: tuple[float, ...]) -> tuple[float, ...]:
    a, b, c, d, e, f = m
    p, q, r, s, t, u = n
    return (
        a * p + c * q,
        b * p + d * q,
        a * r + c * s,
        b * r + d * s,
        a * t + c * u + e,
        b * t + d * u + f,
    )


def path_points(d: str) -> list[tuple[float, float]]:
    tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?", d)
    arity = {"m": 2, "l": 2, "t": 2, "h": 1, "v": 1, "c": 6, "s": 4, "q": 4, "a": 7}
    points: list[tuple[float, float]] = []
    x = y = start_x = start_y = 0.0
    i, command = 0, ""
    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            i += 1
            if command in "zZ":
                x, y = start_x, start_y
                continue
        lower = command.lower()
        args = [float(n) for n in tokens[i : i + arity[lower]]]
        i += arity[lower]
        rel = command.islower()
        if lower == "h":
            x = args[0] + (x if rel else 0)
        elif lower == "v":
            y = args[0] + (y if rel else 0)
        else:
            if lower == "a":
                args = args[5:]
            pairs = list(zip(args[0::2], args[1::2], strict=True))
            for px, py in pairs:
                points.append((px + x, py + y) if rel else (px, py))
            x, y = points[-1]
        points.append((x, y))
        if lower == "m":
            start_x, start_y = x, y
            command = "l" if rel else "L"
    return points


def bbox(element: ET.Element, ctm: tuple[float, ...]) -> list[tuple[float, float]]:
    ctm = compose(ctm, matrix(element.get("transform")))
    tag = element.tag.split("}")[-1]
    local: list[tuple[float, float]] = []
    if tag in ("rect", "image"):
        x, y = float(element.get("x", 0)), float(element.get("y", 0))
        w, h = float(element.get("width")), float(element.get("height"))
        local = [(x, y), (x + w, y + h), (x + w, y), (x, y + h)]
    elif tag in ("circle", "ellipse"):
        cx, cy = float(element.get("cx", 0)), float(element.get("cy", 0))
        rx = float(element.get("rx", element.get("r", 0)))
        ry = float(element.get("ry", element.get("r", 0)))
        local = [
            (cx - rx, cy - ry),
            (cx + rx, cy + ry),
            (cx + rx, cy - ry),
            (cx - rx, cy + ry),
        ]
    elif tag == "path":
        local = path_points(element.get("d", ""))
    elif tag != "g":
        raise SystemExit(f"unhandled SVG element {tag}")
    a, b, c, d, e, f = ctm
    found = [(a * px + c * py + e, b * px + d * py + f) for px, py in local]
    for child in element:
        found += bbox(child, ctm)
    return found


def cut(sheet: Path, names: list[str], dst: Path, gaps: dict[str, str]) -> None:
    """Each named picture of ``sheet`` as name.svg, and name@2.svg at twice the size."""
    root = ET.parse(sheet).getroot()
    if root.get("viewBox"):
        raise SystemExit(f"{sheet.name}: sheets with a viewBox are not handled")
    parents = {child: parent for parent in root.iter() for child in parent}
    ids = {e.get("id"): e for e in root.iter() if e.get("id")}
    dst.mkdir(parents=True, exist_ok=True)
    for name in names:
        element = ids[name]
        ctm: tuple[float, ...] = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        ancestor = parents.get(element)
        chain = []
        while ancestor is not None and ancestor is not root:
            chain.append(ancestor)
            ancestor = parents.get(ancestor)
        for group in reversed(chain):
            ctm = compose(ctm, matrix(group.get("transform")))
        points = bbox(element, ctm)
        left, top = min(p[0] for p in points), min(p[1] for p in points)
        width = max(p[0] for p in points) - left
        height = max(p[1] for p in points) - top
        used = referenced(element, ids)
        for suffix, scale in (("", 1), ("@2", 2)):
            svg = ET.Element(
                f"{{{SVG_NS}}}svg",
                {
                    "width": f"{round(width) * scale}",
                    "height": f"{round(height) * scale}",
                    "viewBox": f"{left:g} {top:g} {width:g} {height:g}",
                },
            )
            if used:
                defs = ET.SubElement(svg, f"{{{SVG_NS}}}defs")
                defs.extend(copy.deepcopy(ids[i]) for i in used)
            wrapper = ET.SubElement(
                svg,
                f"{{{SVG_NS}}}g",
                {"transform": "matrix({:g} {:g} {:g} {:g} {:g} {:g})".format(*ctm)},
            )
            wrapper.append(copy.deepcopy(element))
            text = ET.tostring(svg, encoding="unicode")
            (dst / f"{name}{suffix}.svg").write_text(gapped(text, gaps) + "\n")


def referenced(element: ET.Element, ids: dict[str, ET.Element]) -> list[str]:
    """The ids ``element`` paints with, gradients' own references included, in order."""
    found: list[str] = []
    pending = [element]
    while pending:
        for node in pending.pop().iter():
            for key, value in node.attrib.items():
                refs = re.findall(r"url\(#([^)]+)\)", value)
                if key == XLINK and value.startswith("#"):
                    refs.append(value[1:])
                for ref in refs:
                    if ref in ids and ref not in found and ids[ref] is not element:
                        found.append(ref)
                        pending.append(ids[ref])
    order = {id(e): n for n, e in enumerate(ids.values())}
    return sorted(found, key=lambda i: order[id(ids[i])])


def cinnamon(src: Path, dst: Path) -> None:
    for svg in src.rglob("*"):
        if svg.is_dir():
            continue
        out = dst / svg.relative_to(src)
        out.parent.mkdir(parents=True, exist_ok=True)
        if svg.suffix != ".svg":
            shutil.copy(svg, out)
            continue
        text = gapped(svg.read_text(), CINNAMON_GAPS)
        where = svg.relative_to(src).as_posix()
        if src.name == "assets" and where.startswith(CINNAMON_WHITE):
            text = re.sub("fill:#ffffff", "fill:{{background}}", text, flags=re.I)
        out.write_text(text)


def plank(src: Path) -> str:
    fills = ("FillStartColor", "FillEndColor", "InnerStrokeColor")
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
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK[1:].split("}")[0])
    ET.register_namespace("inkscape", "http://www.inkscape.org/namespaces/inkscape")
    ET.register_namespace(
        "sodipodi", "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
    )
    shutil.rmtree(PACK, ignore_errors=True)

    sass = PACK / "sass"
    shutil.copytree(src / "_sass", sass, ignore=shutil.ignore_patterns("gnome-shell"))
    tweaks = (src / "_sass" / "_tweaks.scss").read_text()
    palette = "\n@import 'color-palette-osiris';\n"
    (sass / "_tweaks-temp.scss").write_text(tweaks + palette)
    (sass / "_color-palette-osiris.scss").write_text(PALETTE)
    upstream_colours = (src / "_sass" / "_colors.scss").read_text()
    (sass / "_colors.scss").write_text(colours(upstream_colours))
    for partial in (sass / "gtk").rglob("*.scss"):
        text = partial.read_text()
        partial.write_text(re.sub(r'(url\("assets/[^"]*)\.png"\)', r'\1.svg")', text))

    for folder, (where, light, dark) in ENTRIES.items():
        (PACK / folder).mkdir()
        stem = "gtk" if folder.startswith("gtk") else folder
        for variant, name in (("light", light), ("dark", dark)):
            text = (src / where / f"{name}.scss").read_text()
            text = re.sub(r"""(['"])(\.\./)+_sass/""", r"\1../sass/", text)
            (PACK / folder / f"{stem}-{variant}.scss").write_text(text)

    common = PACK / "files" / "common"
    pictures = src / "gtk" / "assets"
    for version in ("gtk-3.0", "gtk-4.0"):
        assets = common / version / "assets"
        names = (pictures / "assets.txt").read_text().split()
        cut(pictures / "assets.svg", names, assets, GTK_GAPS)
        # The Nautilus backdrop is drawn only with upstream's "image" tweak,
        # which this pack never sets.
        common_names = [
            name
            for name in (pictures / "assets-common.txt").read_text().split()
            if not name.startswith("backimage")
        ]
        cut(pictures / "assets-common.svg", common_names, assets, GTK_GAPS)
        for svg in (pictures / "assets-common").glob("*.svg"):
            shutil.copy(svg, assets / svg.name)
        shutil.copy(pictures / "logos" / "logo-.svg", assets / "logo.svg")
        shutil.copy(pictures / "logos" / "logo@2-.svg", assets / "logo@2.svg")
    shots = src / "cinnamon" / "assets"
    cinnamon(shots / "common-assets", common / "cinnamon" / "common-assets")
    cinnamon(shots / "assets", PACK / "files" / "light" / "cinnamon" / "assets")
    cinnamon(shots / "assets-Dark", PACK / "files" / "dark" / "cinnamon" / "assets")

    (PACK / "plank").mkdir()
    dock = plank(src / "plank" / "dock.theme")
    for variant in ("light", "dark"):
        (PACK / "plank" / f"dock-{variant}.theme").write_text(dock)

    label = {
        "label": "Qogir",
        "author": "Vince Liuice",
        "version": commit[1],
        "licence": "GPL-3.0",
        "source": "https://github.com/vinceliuice/Qogir-theme",
    }
    (PACK / "skin.json").write_text(json.dumps(label, indent=2) + "\n")
    shutil.copy(upstream / "COPYING", PACK / "LICENSE")
    (PACK / "SOURCES.md").write_text(
        f"Made by shell/skins/make_qogir.py from Qogir-theme {commit[0]}"
        f" ({commit[1]}),\n{label['source']}, GPL-3.0. The Sass and pictures are"
        " upstream's; the\npalette (`sass/_color-palette-osiris.scss`), the cut"
        " of `_colors.scss` it\nreplaces, the GTK pictures cut from upstream's"
        " SVG sheets in place of its\nPNGs, and the gap markers are Osiris's.\n"
    )
    print("wrote", PACK)


if __name__ == "__main__":
    main()
