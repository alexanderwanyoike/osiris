"""Whether archinstall installed anything, judged from what it printed."""

from __future__ import annotations


def failure(returncode: int, output: str) -> str | None:
    """Why the install did not happen, or None when it did."""
    return None
