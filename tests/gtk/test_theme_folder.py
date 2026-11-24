"""An open app hears of Themes added to or removed from the person's folder
by someone else, typically Osiris making one from a prompt."""

from __future__ import annotations

from pathlib import Path

from osiris.apps.theme_folder import ThemeFolder

from .conftest import settle


class Heard:
    def __init__(self) -> None:
        self.times = 0

    def __call__(self) -> None:
        self.times += 1


def test_a_theme_written_to_the_folder_is_heard(tmp_path: Path) -> None:
    """Filming a demo: Osiris made "Ink and Silence" while Appearance was
    open, and its list still said 8 themes until it was reopened."""
    heard = Heard()
    following = ThemeFolder(tmp_path, heard)
    (tmp_path / "ink-and-silence.json").write_text("{}\n")
    assert settle(lambda: heard.times > 0)
    assert following is not None


def test_a_removed_theme_is_heard(tmp_path: Path) -> None:
    (tmp_path / "ink-duel.json").write_text("{}\n")
    heard = Heard()
    following = ThemeFolder(tmp_path, heard)
    (tmp_path / "ink-duel.json").unlink()
    assert settle(lambda: heard.times > 0)
    assert following is not None


def test_a_file_that_is_not_a_theme_is_not_heard(tmp_path: Path) -> None:
    """Each Theme heard rebuilds the list, which loses the place it was
    scrolled to, and an editor's swap file beside a Theme is written often."""
    heard = Heard()
    following = ThemeFolder(tmp_path, heard)
    (tmp_path / ".ink-duel.json.swp").write_text("swap\n")
    settle(lambda: heard.times > 0, seconds=0.5)
    assert heard.times == 0
    assert following is not None
