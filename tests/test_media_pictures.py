"""A generated picture is the person's file, in their Pictures folder."""

from __future__ import annotations

from pathlib import Path

from osiris.harness.media.pictures import Pictures, keep_picture
from osiris.platform import FakeFileSystem

HOME = Path("/home/tester")
FOLDER = HOME / "Pictures/Osiris"


def test_a_picture_is_kept_under_the_themes_name() -> None:
    files = FakeFileSystem()

    path = keep_picture(files, HOME, "misty-forest", b"picture")

    assert path == FOLDER / "misty-forest.png"
    assert files.blobs[path] == b"picture"


def test_an_older_picture_of_that_name_is_never_overwritten() -> None:
    files = FakeFileSystem()
    first = keep_picture(files, HOME, "misty-forest", b"first")

    second = keep_picture(files, HOME, "misty-forest", b"second")
    third = keep_picture(files, HOME, "misty-forest", b"third")

    assert second == FOLDER / "misty-forest-2.png"
    assert third == FOLDER / "misty-forest-3.png"
    assert files.blobs[first] == b"first"


def test_pictures_are_made_by_the_maker_and_kept_in_the_persons_folder() -> None:
    class Maker:
        def make(self, description: str, model: str | None = None) -> bytes:
            return f"{description}{model or ''}".encode()

    files = FakeFileSystem()
    pictures = Pictures(Maker(), files, HOME)

    data = pictures.make("forest")
    path = pictures.keep("misty-forest", data)

    assert path == FOLDER / "misty-forest.png"
    assert files.blobs[path] == b"forest"
    assert pictures.make("forest by ", "vendor/model") == b"forest by vendor/model"
