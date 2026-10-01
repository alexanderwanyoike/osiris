"""Derive a full Osiris palette from a background colour and an accent.

    python3 shell/themes/derive.py '#2e3440' '#88c0d0' --dark --name nord-auto

A theme needs about thirty colours; the creator asks for two. This fills in the
rest, and the result is written into the theme file - it is not recomputed when
the theme is applied. See docs/THEMING.md for why.

Three groups, derived differently:

* **Neutrals** (surface, border, muted text) are the background stepped towards
  the foreground. Pure interpolation, no decisions.
* **State colours** (success, warning, danger) must stay recognisably green,
  amber and red or they stop meaning anything, so their hue is fixed and only
  their saturation and lightness are matched to the palette.
* **Terminal colours** likewise keep their hue - a shell prompt printing red
  has to look red - and are fitted to the palette's depth.
"""
import argparse
import colorsys
import json
import sys

# Hues that carry meaning, in degrees. Only saturation and lightness are
# adapted to the palette; moving these would break what they communicate.
SEMANTIC_HUES = {
    "danger": 2.0,
    "warning": 40.0,
    "success": 130.0,
}
ANSI_HUES = {
    "red": 2.0, "green": 130.0, "yellow": 40.0,
    "blue": 215.0, "magenta": 290.0, "cyan": 185.0,
}

# Relative luminance of mid grey. Backgrounds below this need light text on
# them, whatever the theme calls itself.
MID_LUMINANCE = 0.216


# --------------------------------------------------------------------------- #
# colour helpers

def to_rgb(value: str) -> tuple[float, float, float]:
    v = value.lstrip("#")
    if len(v) != 6:
        raise ValueError(f"{value!r} is not #rrggbb")
    return tuple(int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))


def to_hex(rgb) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}"
                         for c in rgb)


def to_hls(value: str) -> tuple[float, float, float]:
    r, g, b = to_rgb(value)
    return colorsys.rgb_to_hls(r, g, b)


def from_hls(h: float, l: float, s: float) -> str:
    return to_hex(colorsys.hls_to_rgb(h % 1.0, max(0.0, min(1.0, l)),
                                      max(0.0, min(1.0, s))))


def mix(a: str, b: str, t: float) -> str:
    """Blend a towards b by t (0-1)."""
    return to_hex(x + (y - x) * t for x, y in zip(to_rgb(a), to_rgb(b)))


def luminance(value: str) -> float:
    """Relative luminance, WCAG definition."""
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in to_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


# --------------------------------------------------------------------------- #
# derivation

def _foreground(background: str) -> str:
    """Readable text, tinted towards the background's hue.

    A flat white on a green-grey background looks clinical and out of family;
    carrying a little of the background's hue keeps it coherent. The tint is
    then backed off until the contrast ratio is comfortably above the WCAG AAA
    body-text threshold of 7:1.

    Which direction to go is decided by measuring the background, not by the
    theme's declared light/dark flag. Those two can disagree - the creator lets
    you flip the variant before choosing a matching background - and when they
    did, this returned black text on a near-black ground at a contrast ratio of
    1.16. Legibility is not a preference to be honoured.
    """
    hue, _, sat = to_hls(background)
    tint = min(sat, 0.18)
    lighten = luminance(background) < MID_LUMINANCE
    candidate = from_hls(hue, 0.93 if lighten else 0.16, tint)
    step = 0.01 if lighten else -0.01
    for _ in range(12):
        if contrast(candidate, background) >= 7.0:
            return candidate
        candidate = from_hls(hue, to_hls(candidate)[1] + step, tint)
    return "#ffffff" if lighten else "#000000"


def _semantic(hue: float, accent: str, background: str) -> str:
    """A meaning-carrying colour, fitted to the palette's depth.

    Saturation deliberately does NOT follow the accent. A pale accent (Rose
    Pine's mauve, say) dragged "danger" to a washed-out salmon that no longer
    read as an error. These sit in a narrow band that stays recognisable -
    measured against the hand-tuned palettes - with only a light pull towards
    the accent so they do not look pasted on.
    """
    _, _, accent_s = to_hls(accent)
    sat = 0.42 + (min(accent_s, 0.8) - 0.5) * 0.30      # ~0.33-0.51
    # As in _foreground: measured against the background, not the declared
    # variant. Walking the wrong way here never reaches the contrast floor, and
    # the loop falls out with an unreadable colour.
    lighten = luminance(background) < MID_LUMINANCE
    light = 0.64 if lighten else 0.44
    candidate = from_hls(hue / 360.0, light, sat)
    for _ in range(14):
        if contrast(candidate, background) >= 4.0:
            return candidate
        light += 0.03 if lighten else -0.03
        candidate = from_hls(hue / 360.0, light, sat)
    return candidate


def derive(background: str, accent: str, dark: bool = True,
           secondary: str | None = None) -> dict:
    """Return {"colors": {...}, "terminal": {...}} for the given seeds."""
    for label, value in (("background", background), ("accent", accent)):
        to_rgb(value)                                  # validates, raises early
    foreground = _foreground(background)

    colors = {
        "background": background,
        # Neutrals: the background stepped towards the text colour. Small,
        # even steps keep the surfaces distinguishable without banding.
        "surface": mix(background, foreground, 0.06),
        "surfaceMuted": mix(background, foreground, 0.13),
        "border": mix(background, foreground, 0.20),
        "borderActive": accent,
        "foreground": foreground,
        # 0.42 looked right in isolation but produced muted text far darker
        # than any hand-tuned palette; measured against those, ~0.26 matches.
        "foregroundMuted": mix(foreground, background, 0.26),
        "accent": accent,
        "accentMuted": mix(accent, background, 0.45),
    }
    for name, hue in SEMANTIC_HUES.items():
        colors[name] = _semantic(hue, accent, background)

    # ANSI: black and white are palette neutrals; the six hues are fitted the
    # same way as the state colours so the terminal matches the desktop.
    normals = {name: _semantic(hue, accent, background)
               for name, hue in ANSI_HUES.items()}
    order = ["red", "green", "yellow", "blue", "magenta", "cyan"]
    lighten = luminance(background) < MID_LUMINANCE
    terminal = {"regular0": colors["surfaceMuted"], "regular7": foreground,
                "bright0": colors["border"],
                "bright7": mix(foreground, "#ffffff", 0.5 if lighten else 0.0)}
    for index, name in enumerate(order, start=1):
        terminal[f"regular{index}"] = normals[name]
        terminal[f"bright{index}"] = mix(
            normals[name], "#ffffff" if lighten else "#000000", 0.22)

    result = {"colors": colors,
              "terminal": {k: terminal[k] for k in sorted(
                  terminal, key=lambda s: (s.startswith("bright"), s))}}
    if secondary:
        to_rgb(secondary)
        result["colors"]["accentSecondary"] = secondary
    return result


def build(name: str, label: str, background: str, accent: str,
          dark: bool = True, secondary: str | None = None) -> dict:
    """A complete theme document, ready to write to disk."""
    derived = derive(background, accent, dark, secondary)
    theme = {
        "name": name,
        "label": label,
        "dark": dark,
        # Recorded so the creator can reopen the theme with its inputs in
        # place. The engine ignores it; hand-edits to "colors" always win.
        "derived_from": {"background": background, "accent": accent,
                         **({"secondary": secondary} if secondary else {})},
        "colors": derived["colors"],
        "terminal": derived["terminal"],
        "ui": {
            "gtk": "adw-gtk3-dark" if dark else "adw-gtk3",
            "icons": "Papirus-Dark" if dark else "Papirus-Light",
            "cursor": "Adwaita",
            "font": "Noto Sans 10",
            "mono": "FiraCode Nerd Font",
        },
        "requires": ["adw-gtk-theme", "papirus-icon-theme",
                     "noto-fonts", "ttf-firacode-nerd"],
        "wallpaper": "generated",
    }
    return theme


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("background")
    parser.add_argument("accent")
    parser.add_argument("--secondary")
    parser.add_argument("--name", default="custom")
    parser.add_argument("--label")
    parser.add_argument("--light", action="store_true")
    args = parser.parse_args()

    try:
        theme = build(args.name, args.label or args.name.title(),
                      args.background, args.accent,
                      dark=not args.light, secondary=args.secondary)
    except ValueError as error:
        sys.exit(f"error: {error}")
    print(json.dumps(theme, indent=4))


if __name__ == "__main__":
    main()
