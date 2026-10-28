"""What the make_*.py scripts share.

Each edit a maker makes to upstream's source stops it when upstream has moved,
so a regenerated pack never silently loses the Theme's colours.
"""

import re


def replace(text: str, old: str, new: str, where: str) -> str:
    if old not in text:
        raise SystemExit(f"upstream changed: {old!r} not in {where}")
    return text.replace(old, new)


def replace_once(text: str, old: str, new: str, where: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"upstream changed: expected {old!r} once in {where}")
    return text.replace(old, new)


class Recolour:
    """Upstream's colours as gaps, in whatever case upstream wrote them."""

    def __init__(self, gaps: dict[str, str]) -> None:
        self.gaps = gaps

    def __call__(self, text: str) -> str:
        for colour, gap in self.gaps.items():
            text = re.sub(re.escape(colour), gap, text, flags=re.IGNORECASE)
        return text
