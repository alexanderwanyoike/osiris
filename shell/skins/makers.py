"""What the make_*.py scripts share.

Each edit a maker makes to upstream's source stops it when upstream has moved,
so a regenerated pack never silently loses the Theme's colours.
"""

import re
import shutil
from collections.abc import Callable
from pathlib import Path


def rewrite(pack: Path, make: Callable[[Path], None]) -> None:
    """Make the pack afresh beside it, and swap it in only once making finished."""
    staging = pack.with_name(f".{pack.name}.new")
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    try:
        make(staging)
    except BaseException:
        shutil.rmtree(staging)
        raise
    shutil.rmtree(pack, ignore_errors=True)
    staging.rename(pack)


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
        self.matched: set[str] = set()

    def __call__(self, text: str) -> str:
        for colour, gap in self.gaps.items():
            text, count = re.subn(re.escape(colour), gap, text, flags=re.IGNORECASE)
            if count:
                self.matched.add(colour)
        return text

    def check(self, where: str) -> None:
        """Stop unless every colour matched in some text since this was made."""
        for colour in self.gaps:
            if colour not in self.matched:
                raise SystemExit(f"upstream changed: {colour!r} matched nothing in {where}")
