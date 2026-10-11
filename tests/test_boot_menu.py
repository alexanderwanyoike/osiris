"""The install medium's boot menus, rebranded from archiso's releng profile."""

from __future__ import annotations

import pytest

from osiris.iso.boot_menu import rebranded, themed

SYSLINUX_ENTRY = "MENU LABEL Arch Linux install medium (%ARCH%, BIOS)\n"


def test_entries_are_called_osiris() -> None:
    assert rebranded(SYSLINUX_ENTRY) == (
        "MENU LABEL Osiris install medium (%ARCH%, BIOS)\n"
    )


def test_text_without_an_entry_name_is_unchanged() -> None:
    assert rebranded("timeout 15\n") == "timeout 15\n"


# The graphics block of releng's grub/grub.cfg, followed by the serial console
# it appends afterwards.
RELENG_GRUB = """\
if loadfont "${prefix}/fonts/unicode.pf2" ; then
    insmod all_video
    set gfxmode="auto"
    terminal_input console
    terminal_output console
fi

if serial --unit=0 --speed=115200; then
    terminal_input --append serial
    terminal_output --append serial
fi
"""

THEME_DIR = "/boot/grub/themes/osiris"
FONTS = ["Osiris-Sans-18.pf2", "Osiris-Mono-16.pf2"]


def themed_releng() -> str:
    return themed(RELENG_GRUB, THEME_DIR, FONTS)


def test_the_menu_draws_with_the_osiris_theme() -> None:
    assert f"set theme={THEME_DIR}/theme.txt" in themed_releng()


def test_the_menu_draws_on_the_graphical_terminal() -> None:
    lines = [line.strip() for line in themed_releng().splitlines()]
    assert "terminal_output gfxterm" in lines
    assert "terminal_output console" not in lines


def test_every_theme_font_is_loaded_before_the_theme() -> None:
    text = themed_releng()
    theme_at = text.index("set theme=")
    for font in FONTS:
        assert -1 < text.find(f"loadfont {THEME_DIR}/{font}") < theme_at


def test_the_serial_console_is_kept() -> None:
    assert "terminal_output --append serial" in themed_releng()


def test_a_menu_without_releng_graphics_block_is_refused() -> None:
    with pytest.raises(ValueError):
        themed("timeout=15\n", THEME_DIR, FONTS)
