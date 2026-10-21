"""The slides the installer shows while it installs."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from osiris.iso import package

REPOSITORY = Path(__file__).resolve().parent.parent
SLIDES = REPOSITORY / "apps" / "installer" / "slides"


def test_every_slide_is_a_picture_with_one_sentence() -> None:
    slides = json.loads((SLIDES / "slides.json").read_text())
    assert len(slides) >= 3
    for slide in slides:
        assert (SLIDES / slide["image"]).is_file()
        assert slide["caption"].endswith(".")
        assert slide["caption"].count(". ") == 0


def test_the_package_carries_the_slides_as_files_not_links(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The links point into docs/, which the package does not carry."""
    # iso/repo.py puts provision/ on the path, where it would shadow names.
    monkeypatch.setattr(sys, "path", list(sys.path))
    spec = importlib.util.spec_from_file_location(
        "repo", REPOSITORY / "iso" / "repo.py"
    )
    assert spec is not None and spec.loader is not None
    repo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(repo)
    repo.stage(str(tmp_path))
    staged = tmp_path / "root" / package.SOURCE_DIR.lstrip("/") / "apps" / "installer"
    for slide in json.loads((SLIDES / "slides.json").read_text()):
        picture = staged / "slides" / slide["image"]
        assert picture.is_file()
        assert not picture.is_symlink()
