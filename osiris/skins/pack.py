"""A skinpack: a Skin's label and style sheets, with gaps for the Theme's colours."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

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
