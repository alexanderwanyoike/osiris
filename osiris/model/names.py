"""Names made from what a person calls something."""

from __future__ import annotations

import re


def slug(label: str) -> str:
    """A name from a human label, for a theme or a Program.

    Names index files, folders and generated theme directories, so they have to
    survive being a filename and a GTK theme name on every filesystem we care
    about.
    """
    out = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return out or "untitled"


def is_slug(name: str) -> bool:
    return slug(name) == name
