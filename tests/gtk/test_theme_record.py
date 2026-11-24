"""An open app hears of a Theme applied by someone else, typically Osiris
applying one it made from a prompt."""

from __future__ import annotations

from pathlib import Path

from osiris.apps.theme_record import ThemeRecord

from .conftest import settle


def test_a_theme_applied_elsewhere_is_heard(tmp_path: Path) -> None:
    """Filming a demo: Osiris applied "Ink and Silence" while Appearance was
    open, and Appearance kept the old Theme's card selected."""
    record = tmp_path / "theme"
    record.write_text("ink-duel\n")
    heard: list[str] = []
    following = ThemeRecord(record, heard.append)
    record.write_text("ink-and-silence\n")
    assert settle(lambda: heard[-1:] == ["ink-and-silence"])
    assert following is not None
