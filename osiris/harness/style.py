"""The drawer's colours, from the Theme, and the choice of Skin.

The Theme supplies colours and nothing else: here they become GTK colour
variables and a GtkSourceView scheme. A Skin is a stylesheet that may only
refer to those variables (CONTEXT.md: a Skin never carries colour), so any
Skin works under any Theme.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from xml.sax.saxutils import quoteattr

from osiris.harness.markdown import InlineStyle

#: One id whatever the Theme, so switching rewrites the scheme in place.
SCHEME_ID = "osiris"
#: Relative to the home; GtkSourceView looks here for user schemes.
SCHEME_FILE = ".local/share/gtksourceview-5/styles/osiris.xml"
#: Relative to the home: the chosen Skin's name, as plain text.
SKIN_FILE = ".config/osiris/harness/skin"

SKINS = ("bubbles", "transcript")
DEFAULT_SKIN = "bubbles"

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


def inline_style(theme: Mapping[str, Any]) -> InlineStyle:
    c = _colours(theme)
    return InlineStyle(
        code_foreground=c["foreground"], code_background=c["surfaceMuted"]
    )


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
            "foreground": c["foregroundMuted"],
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
