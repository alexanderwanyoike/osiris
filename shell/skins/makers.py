"""What the make_*.py scripts share.

Each edit a maker makes to upstream's source stops it when upstream has moved,
so a regenerated pack never silently loses the Theme's colours.
"""


def replace(text: str, old: str, new: str, where: str) -> str:
    if old not in text:
        raise SystemExit(f"upstream changed: {old!r} not in {where}")
    return text.replace(old, new)
