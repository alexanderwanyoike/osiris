"""The slides the installer shows while it installs."""

from __future__ import annotations

import json
from pathlib import Path

SLIDES = Path(__file__).resolve().parent.parent / "apps" / "installer" / "slides"


def test_every_slide_is_a_picture_with_one_sentence() -> None:
    slides = json.loads((SLIDES / "slides.json").read_text())
    assert len(slides) >= 3
    for slide in slides:
        assert (SLIDES / slide["image"]).is_file()
        assert slide["caption"].endswith(".")
        assert slide["caption"].count(". ") == 0
