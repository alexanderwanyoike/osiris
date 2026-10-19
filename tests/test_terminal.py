"""The terminal's look as a ghostty theme Osiris owns, named from a config the
person keeps."""

from __future__ import annotations

from osiris.provision.seeding import may_write
from osiris.themes.terminal import CONFIG, THEME, theme_file

NORD = {
    "colors": {
        "background": "#2e3440",
        "foreground": "#d8dee9",
        "accent": "#88c0d0",
        "surfaceMuted": "#3b4252",
    },
    "terminal": {"regular0": "#3b4252", "bright7": "#eceff4"},
}


def test_the_theme_file_carries_the_palette_and_the_mono_font() -> None:
    text = theme_file(NORD, mono="FiraCode Nerd Font")
    assert "background = #2e3440" in text
    assert "cursor-color = #88c0d0" in text
    assert "palette = 0=#3b4252" in text
    assert "palette = 15=#eceff4" in text
    assert "font-family = FiraCode Nerd Font" in text


def test_the_persons_config_names_the_osiris_theme() -> None:
    assert f"theme = {THEME}" in CONFIG.splitlines()


def test_the_persons_config_sets_nothing_the_theme_does() -> None:
    settings = {
        line.split("=")[0].strip() for line in CONFIG.splitlines() if "=" in line
    }
    assert settings == {"theme"}


def test_once_seeded_the_persons_config_is_theirs() -> None:
    assert not may_write(CONFIG)
