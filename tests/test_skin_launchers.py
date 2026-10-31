"""The launcher themes shipped Skins bring, filled in a Theme's colours."""

from __future__ import annotations

import json
import re
from pathlib import Path

from osiris.skins.pack import fill, gaps

ROOT = Path(__file__).resolve().parent.parent


def entry(skin: str) -> dict[str, str]:
    theme = json.loads((ROOT / "shell" / "themes" / "rose-pine.json").read_text())
    rasi = (ROOT / "shell" / "skins" / skin / "rofi" / "launcher.rasi").read_text()
    filled = fill(rasi, gaps(theme))
    defined = dict(re.findall(r"([\w-]+):\s*([^;]+);", filled.split("}")[0]))
    body = re.search(r"\bentry\s*\{([^}]*)\}", filled)
    assert body
    found = dict(re.findall(r"([\w-]+):\s*([^;]+);", body[1]))
    return {k: defined.get(v.lstrip("@"), v) for k, v in found.items()}


def test_colloids_placeholder_is_not_drawn_as_typed_text() -> None:
    colours = entry("colloid")
    assert colours["placeholder-color"] != colours["text-color"]
