"""The shipped Skins as their makers leave them."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

SKINS = Path(__file__).resolve().parent.parent / "shell" / "skins"
SVG = "{http://www.w3.org/2000/svg}"
CUT = sorted(
    (SKINS / "orchis" / "files" / "common" / "gtk-3.0" / "assets").glob("*.svg")
)


@pytest.mark.parametrize("picture", CUT, ids=lambda p: p.name)
def test_a_picture_cut_from_orchiss_sheet_carries_only_the_defs_it_uses(
    picture: Path,
) -> None:
    text = picture.read_text()
    defs = ET.fromstring(text).find(f"{SVG}defs")
    carried = [] if defs is None else [d.get("id") for d in defs]
    used = set(re.findall(r"""(?:url\(#|"#)([^)"]+)""", text))
    assert [i for i in carried if i not in used] == []
