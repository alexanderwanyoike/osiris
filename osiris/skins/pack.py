"""A skinpack: a Skin's label and style sheets, with gaps for the Theme's colours."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LABEL_FILE = "skin.json"
LABEL_FIELDS = ("label", "author", "version", "licence", "source")


class SkinpackError(ValueError):
    """A folder that cannot be used as a skinpack, and why."""


@dataclass(frozen=True)
class Skinpack:
    name: str
    label: str
    author: str
    version: str
    licence: str
    source: str
    root: Path


def read(root: Path) -> Skinpack:
    try:
        label = json.loads((root / LABEL_FILE).read_text())
    except FileNotFoundError:
        raise SkinpackError(f"{root.name}: no {LABEL_FILE}") from None
    missing = [field for field in LABEL_FIELDS if not isinstance(label.get(field), str)]
    if missing:
        raise SkinpackError(f"{root.name}: {LABEL_FILE} lacks {', '.join(missing)}")
    return Skinpack(
        name=root.name,
        label=label["label"],
        author=label["author"],
        version=label["version"],
        licence=label["licence"],
        source=label["source"],
        root=root,
    )


GAP = re.compile(r"\{\{(\w+)\}\}")
ROLES = (
    "background",
    "surface",
    "foreground",
    "accent",
    "success",
    "warning",
    "danger",
)


def gaps(theme: Mapping[str, Any]) -> dict[str, str]:
    """The Theme's colours by the names a skinpack's gaps use."""
    colours = theme["colors"]
    found = {"variant": "dark" if theme.get("dark", True) else "light"}
    for role in ROLES:
        found[role] = colours[role]
        red, green, blue = (int(colours[role][i : i + 2], 16) for i in (1, 3, 5))
        found[f"{role}_plank"] = f"{red};;{green};;{blue};;255"
    return found


def fill(text: str, filled: Mapping[str, str]) -> str:
    def value(match: re.Match[str]) -> str:
        try:
            return filled[match[1]]
        except KeyError:
            raise SkinpackError(f"unknown gap {{{{{match[1]}}}}}") from None

    return GAP.sub(value, text)


def sass_gaps(filled: Mapping[str, str]) -> str:
    """The gaps as the Sass variables a skinpack's palette reads."""
    return "".join(
        f"$gap-{name}: {value!r};\n"
        if name == "variant"
        else f"$gap-{name}: {value};\n"
        for name, value in filled.items()
        if not name.endswith("_plank")
    )
