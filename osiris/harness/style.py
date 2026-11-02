"""The drawer's colours, from the Theme, and the choice of Skin.

The Theme supplies colours and nothing else: here they become GTK colour
variables and a GtkSourceView scheme. A Skin is a stylesheet that may only
refer to those variables (CONTEXT.md: a Skin never carries colour), so any
Skin works under any Theme.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import quoteattr

from osiris.harness.markdown import InlineStyle
from osiris.model.colour import Colour

#: One id whatever the Theme, so switching rewrites the scheme in place.
SCHEME_ID = "osiris"
#: Relative to the home; GtkSourceView looks here for user schemes.
SCHEME_FILE = ".local/share/gtksourceview-5/styles/osiris.xml"
#: Relative to the home: the chosen Skin's name, as plain text.
SKIN_FILE = ".config/osiris/harness/skin"

SKINS = ("bubbles", "transcript", "studio")
DEFAULT_SKIN = "studio"

#: The colours a Skin may refer to, and nothing else.
VARIABLES = (
    "harness_bg",
    "harness_fg",
    "harness_muted",
    "harness_border",
    "harness_accent",
    "harness_on_accent",
    "harness_raised",
    "harness_sunken",
    "harness_success",
    "harness_warning",
    "harness_danger",
    "harness_glass",
    "harness_glass_edge",
)


def _colours(theme: Mapping[str, Any]) -> Mapping[str, str]:
    colours: Mapping[str, str] = theme["colors"]
    return colours


def _luminance(hex_colour: str) -> float:
    channels = [int(hex_colour.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [
        c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def on_accent(theme: Mapping[str, Any]) -> str:
    """The palette's background or foreground, whichever reads on the accent."""
    c = _colours(theme)
    return max(
        (c["background"], c["foreground"]), key=lambda t: _contrast(t, c["accent"])
    )


#: Glass is the raised surface lifted toward the text colour and tinted with the
#: accent, so it frosts in the Theme's own colour rather than in white.
GLASS_LIFT = 0.07
GLASS_EDGE_LIFT = 0.22
GLASS_TINT = 0.10


#: How far line numbers fade from muted text toward the background.
GUTTER_FADE = 0.45
#: How far a token's background fades from the accent to the surface.
TOKEN_WASH = 0.8


def _frosted(c: Mapping[str, str], *, lift: float) -> str:
    lifted = Colour(c["surfaceMuted"]).mix(Colour(c["foreground"]), lift)
    return lifted.mix(Colour(c["accent"]), GLASS_TINT).hex


def colours_css(theme: Mapping[str, Any]) -> str:
    c = _colours(theme)
    own = {
        "harness_bg": c["surface"],
        "harness_fg": c["foreground"],
        "harness_muted": c["foregroundMuted"],
        "harness_border": c["border"],
        "harness_accent": c["accent"],
        "harness_on_accent": on_accent(theme),
        "harness_raised": c["surfaceMuted"],
        "harness_sunken": c["background"],
        "harness_success": c["success"],
        "harness_warning": c["warning"],
        "harness_danger": c["danger"],
        "harness_glass": _frosted(c, lift=GLASS_LIFT),
        "harness_glass_edge": _frosted(c, lift=GLASS_EDGE_LIFT),
    }
    # libadwaita draws the entry and buttons from its own variables; without
    # these they would keep libadwaita's grey inside an Osiris-coloured drawer.
    adwaita = {
        "window_bg_color": c["surface"],
        "window_fg_color": c["foreground"],
        "view_bg_color": c["background"],
        "view_fg_color": c["foreground"],
        "accent_color": c["accent"],
        "accent_bg_color": c["accent"],
        "accent_fg_color": on_accent(theme),
        "card_bg_color": c["surfaceMuted"],
        "card_fg_color": c["foreground"],
        "sidebar_bg_color": c["surfaceMuted"],
        "sidebar_fg_color": c["foreground"],
        "sidebar_backdrop_color": c["surfaceMuted"],
        "popover_bg_color": c["surface"],
        "popover_fg_color": c["foreground"],
        "borders": c["border"],
    }
    lines = [
        f"@define-color {name} {value};" for name, value in {**own, **adwaita}.items()
    ]
    return "\n".join(lines) + "\n"


def code_font_css(theme: Mapping[str, Any]) -> str:
    """Code in the font the terminal uses, ligatures on as ghostty has them,
    at one size and line height for every look."""
    mono = theme.get("ui", {}).get("mono", "monospace")
    return (
        ".harness-code, .harness-code text {\n"
        f'    font-family: "{mono}";\n'
        '    font-feature-settings: "calt", "liga";\n'
        "    font-size: 0.92em;\n"
        "}\n"
    )


def inline_style(theme: Mapping[str, Any]) -> InlineStyle:
    c = _colours(theme)
    return InlineStyle(
        code_foreground=c["foreground"], code_background=c["surfaceMuted"]
    )


#: How far the context ring's track lifts from the card toward the text.
TRACK_LIFT = 0.12
#: How much more vivid than the Theme's colours the ring is: it warns.
VIVID = 1.35


@dataclass(frozen=True)
class RingColours:
    track: str
    accent: str
    danger: str

    def at(self, alarm: float) -> str:
        """The ring's colour ``alarm`` of the way from the accent to danger.
        Turned in OKLCH, the short way round the hues, so it keeps its
        colour on the way rather than greying as an RGB mix does."""
        calm, full = Colour(self.accent).oklch, Colour(self.danger).oklch
        turn = (full[2] - calm[2] + 180) % 360 - 180
        return Colour.from_oklch(
            calm[0] + (full[0] - calm[0]) * alarm,
            (calm[1] + (full[1] - calm[1]) * alarm) * VIVID,
            calm[2] + turn * alarm,
        ).hex


def ring_colours(theme: Mapping[str, Any]) -> RingColours:
    """The context ring's colours, drawn on a card's raised surface."""
    c = _colours(theme)
    track = Colour(c["surfaceMuted"]).mix(Colour(c["foreground"]), TRACK_LIFT)
    return RingColours(track.hex, c["accent"], c["danger"])


def token_colours(theme: Mapping[str, Any]) -> tuple[str, str]:
    """A picked file or skill in the message box: foreground and background."""
    c = _colours(theme)
    wash = Colour(c["accent"]).mix(Colour(c["surface"]), TOKEN_WASH)
    return c["accent"], wash.hex


def source_scheme(theme: Mapping[str, Any]) -> str:
    """A GtkSourceView scheme: code on the sunken background, syntax in the
    terminal colours, so a snippet looks as it will in ghostty."""
    c = _colours(theme)
    t: Mapping[str, str] = theme["terminal"]
    styles: dict[str, dict[str, str]] = {
        "text": {"foreground": c["foreground"], "background": c["background"]},
        "selection": {"foreground": c["foreground"], "background": c["accentMuted"]},
        "selection-unfocused": {"background": c["surfaceMuted"]},
        "cursor": {"foreground": c["accent"]},
        "current-line": {"background": c["surface"]},
        "line-numbers": {
            "foreground": Colour(c["foregroundMuted"])
            .mix(Colour(c["background"]), GUTTER_FADE)
            .hex,
            "background": c["background"],
        },
        "bracket-match": {"background": c["surfaceMuted"], "bold": "true"},
        "def:comment": {"foreground": c["foregroundMuted"], "italic": "true"},
        "def:string": {"foreground": t["regular2"]},
        "def:number": {"foreground": t["regular3"]},
        "def:constant": {"foreground": t["regular3"]},
        "def:special-char": {"foreground": t["regular3"]},
        "def:keyword": {"foreground": t["regular5"]},
        "def:statement": {"foreground": t["regular5"]},
        "def:preprocessor": {"foreground": t["regular5"]},
        "def:type": {"foreground": t["regular6"]},
        "def:builtin": {"foreground": t["regular6"]},
        "def:function": {"foreground": t["regular4"]},
        "def:identifier": {"foreground": c["foreground"]},
        "def:operator": {"foreground": c["foregroundMuted"]},
        "def:error": {"foreground": c["danger"], "underline": "error"},
        "def:warning": {"foreground": c["warning"]},
        "def:note": {"foreground": c["accent"], "bold": "true"},
        "def:heading": {"foreground": c["accent"], "bold": "true"},
        "def:emphasis": {"italic": "true"},
        "def:strong-emphasis": {"bold": "true"},
        "def:inline-code": {"foreground": t["regular2"]},
        "def:link-text": {"foreground": c["accent"]},
        "def:net-address": {"foreground": c["accent"], "underline": "single"},
        "def:insertion": {"foreground": c["success"]},
        "def:deletion": {"foreground": c["danger"]},
        "diff:added-line": {"foreground": c["success"]},
        "diff:removed-line": {"foreground": c["danger"]},
    }
    body = "\n".join(
        "  <style name={}{}/>".format(
            quoteattr(name),
            "".join(f" {key}={quoteattr(value)}" for key, value in attrs.items()),
        )
        for name, attrs in styles.items()
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<style-scheme id="{SCHEME_ID}" name="Osiris" version="1.0">\n'
        "  <description>Generated by Osiris from the current Theme.</description>\n"
        f"{body}\n"
        "</style-scheme>\n"
    )


def skin_name(text: str | None) -> str:
    """The Skin named in SKIN_FILE, or the default for anything unknown."""
    name = (text or "").strip()
    return name if name in SKINS else DEFAULT_SKIN
