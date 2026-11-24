"""A wide picture size that an image model's published schema allows."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

FULL_HD = {"width": 1920, "height": 1080}
_WIDE_PRESET = "landscape_16_9"


def wide_size(field: Mapping[str, Any]) -> object:
    """What to send as ``image_size``, or None to leave it to the model.

    Limits on exact sizes appear only in a schema's prose and differ by model,
    so a model that states any gets its own preset rather than a guessed size.
    """
    kinds = field.get("anyOf") or [field]
    presets = [value for kind in kinds for value in kind.get("enum", ())]
    limited = "must" in str(field.get("description", "")).lower()
    if any("$ref" in kind for kind in kinds) and not limited:
        return FULL_HD
    return _WIDE_PRESET if _WIDE_PRESET in presets else _widest(presets)


def _widest(presets: list[object]) -> str | None:
    sizes = []
    for preset in presets:
        exact = re.fullmatch(r"([1-9]\d*)x([1-9]\d*)", str(preset))
        if exact:
            width, height = int(exact[1]), int(exact[2])
            sizes.append((width / height, width * height, str(preset)))
    return max(sizes)[2] if sizes else None
