"""The image model a person has made their default."""

from __future__ import annotations

from pathlib import Path

from osiris.harness.media.model_setting import MODEL_FILE, save_model, saved_model
from osiris.platform import FakeFileSystem, RealFileSystem

HOME = Path("/home/tester")


def test_no_model_is_saved_until_the_person_chooses_one() -> None:
    assert saved_model(FakeFileSystem(), HOME) is None


def test_a_chosen_model_reads_back_as_plain_text() -> None:
    files = FakeFileSystem()

    save_model(files, HOME, "vendor/model")

    assert saved_model(files, HOME) == "vendor/model"
    assert files.read(HOME / MODEL_FILE) == "vendor/model\n"


def test_clearing_the_choice_goes_back_to_the_default() -> None:
    files = FakeFileSystem()
    save_model(files, HOME, "vendor/model")

    save_model(files, HOME, None)

    assert saved_model(files, HOME) is None
    assert not files.exists(HOME / MODEL_FILE)


def test_a_file_that_cannot_be_read_counts_as_no_choice(tmp_path: Path) -> None:
    path = tmp_path / MODEL_FILE
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\xff\xfe")

    assert saved_model(RealFileSystem(), tmp_path) is None
