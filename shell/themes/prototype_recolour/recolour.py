"""PROTOTYPE, throwaway: recolour a GTK 3 theme into an Osiris Theme by role.

    python3 recolour.py <theme's gtk.css> <output gtk.css> <osiris theme name>

What it found is in NOTES.md beside it; the real thing is built test-first.
"""
import json, re, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from osiris.model.colour import Colour

LITERAL = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*[\d.]+\s*)?\)")

def parse(text):
    if text.startswith("#"):
        h = text[1:]
        if len(h) == 3: h = "".join(c * 2 for c in h)
        return Colour("#" + h.lower()), None
    nums = [float(n) for n in re.findall(r"[\d.]+", text)]
    return Colour("#%02x%02x%02x" % tuple(int(n) for n in nums[:3])), (nums[3] if len(nums) == 4 else None)

def render(c, a):
    if a is None: return c.hex
    r, g, b = (round(v * 255) for v in c.rgb)
    return f"rgba({r}, {g}, {b}, {a})"

def rule(css, selector_re, prop):
    """The first literal colour a property takes in a rule whose selector matches."""
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        if re.search(selector_re, m.group(1)):
            p = re.search(rf"(?:^|;|\s){prop}\s*:\s*({LITERAL.pattern})", m.group(2))
            if p: return parse(p.group(1))[0]
    return None

def roles(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    bg = rule(css, r"(^|,)\s*(window|\.background)\s*(,|$)", "background-color")
    fg = rule(css, r"(^|,)\s*(window|\.background)\s*(,|$)", "color") or rule(css, r"(^|,)\s*\*\s*(,|$)", "color")
    accent = rule(css, r":selected|selection", "background-color")
    return bg, fg, accent

def fallback(css):
    from collections import Counter
    found = [parse(m.group(0))[0] for m in LITERAL.finditer(css)]
    counts = Counter(c.hex for c in found if c.oklch[1] < 0.05)
    mean = sum(Colour(h).oklch[0] * n for h, n in counts.items()) / sum(counts.values())
    darks = [h for h in counts if Colour(h).oklch[0] < 0.5]
    lights = [h for h in counts if Colour(h).oklch[0] >= 0.5]
    dark = mean < 0.5
    return Colour(max(darks if dark else lights, key=counts.get)), Colour(max(lights if dark else darks, key=counts.get))

ON_ACCENT = re.compile(r"suggested-action|:checked|:selected|selection|\.accent")

def readable_on(colour, choices):
    return max(choices, key=lambda c: c.contrast(colour))

def recolour(css, palette):
    base_bg, base_fg, base_accent = roles(css)
    if base_bg is None or base_fg is None:
        base_bg, base_fg = fallback(css)
    if base_accent is None:
        base_accent = Colour("#3584e4")
    print("roles:", base_bg and base_bg.hex, base_fg and base_fg.hex, base_accent and base_accent.hex, file=sys.stderr)
    bg, fg = Colour(palette["background"]), Colour(palette["foreground"])
    bl, fl = base_bg.oklch[0], base_fg.oklch[0]
    ob, of = bg.oklch[0], fg.oklch[0]
    def neutral(L):
        t = (L - bl) / (fl - bl)
        if 0 <= t <= 1: return bg.mix(fg, t)
        _, chroma, hue = bg.oklch
        return Colour.from_oklch(max(0.0, min(1.0, ob + t * (of - ob))), chroma, hue)
    def one(m):
        c, a = parse(m.group(0))
        L, C, h = c.oklch
        if C < 0.05: return render(neutral(L), a)
        if h < 45 or h > 330: role = "danger"
        elif 100 < h < 165: role = "success"
        elif 60 < h <= 100: role = "warning"
        else: role = "accent"
        tl, tc, th = Colour(palette[role]).oklch
        shift = (L - base_accent.oklch[0]) if role == "accent" else 0
        return render(Colour.from_oklch(max(0.05, min(0.97, tl + shift)), tc, th), a)
    out = LITERAL.sub(one, css)
    # Text on the accent takes whichever end of the palette reads on it.
    on_accent = readable_on(Colour(palette["accent"]), [bg, fg]).hex
    def text_on_accent(m):
        if not ON_ACCENT.search(m.group(1)):
            return m.group(0)
        body = re.sub(r"(?<![-\w])color\s*:\s*[^;]+;", f"color: {on_accent};", m.group(2))
        return m.group(1) + "{" + body + "}"
    return re.sub(r"([^{}]+)\{([^{}]*)\}", text_on_accent, out)

src, out, theme = sys.argv[1:4]
palette = json.load(open(REPO / "shell" / "themes" / f"{theme}.json"))["colors"]
open(out, "w").write(recolour(open(src).read(), palette))
