"""The install medium's boot menus, rebranded from archiso's releng profile."""

from __future__ import annotations

import pytest

from osiris.iso.boot_menu import (
    grub_with_installer_entry,
    rebranded,
    syslinux_with_installer_entry,
    themed,
    without_apm_entries,
)

SYSLINUX_ENTRY = "MENU LABEL Arch Linux install medium (%ARCH%, BIOS)\n"


def test_entries_boot_the_osiris_live_medium() -> None:
    assert rebranded(SYSLINUX_ENTRY) == (
        "MENU LABEL Osiris live medium (%ARCH%, BIOS)\n"
    )


def test_the_bios_menu_title_is_osiris() -> None:
    assert rebranded("MENU TITLE Arch Linux\n") == "MENU TITLE Osiris\n"


def test_help_text_offers_to_install_osiris() -> None:
    help_text = "It allows you to install Arch Linux or perform system maintenance.\n"
    assert rebranded(help_text) == (
        "It allows you to install Osiris or perform system maintenance.\n"
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


# The end of releng's syslinux/archiso_tail.cfg.
RELENG_SYSLINUX_TAIL = """\
# https://wiki.syslinux.org/wiki/index.php/Hdt_(Hardware_Detection_Tool)
LABEL hdt
MENU LABEL Hardware Information (HDT)
COM32 hdt.c32
APPEND modules_alias=hdt/modalias.gz pciids=hdt/pciids.gz

LABEL reboot
TEXT HELP
Reboot computer.
The computer's firmware must support APM.
ENDTEXT
MENU LABEL Reboot
COM32 reboot.c32

LABEL poweroff
TEXT HELP
Power off computer.
The computer's firmware must support APM.
ENDTEXT
MENU LABEL Power Off
COM32 poweroff.c32
"""


def test_entries_that_need_apm_are_dropped() -> None:
    text = without_apm_entries(RELENG_SYSLINUX_TAIL)
    assert "reboot.c32" not in text
    assert "poweroff.c32" not in text


def test_entries_that_do_not_need_apm_are_kept_whole() -> None:
    text = without_apm_entries(RELENG_SYSLINUX_TAIL)
    assert text.startswith(RELENG_SYSLINUX_TAIL.split("\n\n")[0])


UNIT = "osiris-installer.target"

# releng's first two grub.cfg entries, after rebranding.
RELENG_GRUB_ENTRIES = """\
menuentry "Osiris live medium (%ARCH%, ${archiso_platform})" --class arch --id 'archlinux' {
    set gfxpayload=keep
    linux /%INSTALL_DIR%/boot/%ARCH%/vmlinuz-linux archisobasedir=%INSTALL_DIR% %KERNEL_PARAMS%
    initrd /%INSTALL_DIR%/boot/%ARCH%/initramfs-linux.img
}

menuentry "Osiris live medium with speakup screen reader (%ARCH%, ${archiso_platform})" --id 'archlinux-accessibility' {
    set gfxpayload=keep
    linux /%INSTALL_DIR%/boot/%ARCH%/vmlinuz-linux accessibility=on %KERNEL_PARAMS%
    initrd /%INSTALL_DIR%/boot/%ARCH%/initramfs-linux.img
}
"""  # noqa: E501


def grub_entries(text: str) -> list[str]:
    return [block for block in text.split("\n\n") if block.startswith("menuentry")]


def test_grub_offers_the_installer_second() -> None:
    entries = grub_entries(grub_with_installer_entry(RELENG_GRUB_ENTRIES, UNIT))
    assert len(entries) == 3
    assert entries[1].startswith('menuentry "Osiris installer only (%ARCH%')
    assert "--id 'osiris-installer'" in entries[1]


def test_grubs_installer_entry_boots_the_installer_target() -> None:
    entries = grub_entries(grub_with_installer_entry(RELENG_GRUB_ENTRIES, UNIT))
    assert f"%KERNEL_PARAMS% systemd.unit={UNIT}\n" in entries[1]


def test_grubs_live_entry_is_unchanged() -> None:
    entries = grub_entries(grub_with_installer_entry(RELENG_GRUB_ENTRIES, UNIT))
    assert entries[0] == grub_entries(RELENG_GRUB_ENTRIES)[0]


def test_a_grub_menu_without_releng_entry_is_refused() -> None:
    with pytest.raises(ValueError):
        grub_with_installer_entry("timeout=15\n", UNIT)


# releng's syslinux/archiso_sys-linux.cfg, after rebranding.
RELENG_SYSLINUX_ENTRIES = """\
LABEL arch
TEXT HELP
Boot the Osiris live medium on BIOS.
It allows you to install Osiris or perform system maintenance.
ENDTEXT
MENU LABEL Osiris live medium (%ARCH%, BIOS)
LINUX /%INSTALL_DIR%/boot/%ARCH%/vmlinuz-linux
APPEND archisobasedir=%INSTALL_DIR% %KERNEL_PARAMS%

# Accessibility boot option
LABEL archspeech
MENU LABEL Osiris live medium (%ARCH%, BIOS) with ^speech
APPEND archisobasedir=%INSTALL_DIR% accessibility=on %KERNEL_PARAMS%
"""


def syslinux_entries(text: str) -> list[str]:
    return text.rstrip("\n").split("\n\n")


def test_syslinux_offers_the_installer_second() -> None:
    entries = syslinux_entries(
        syslinux_with_installer_entry(RELENG_SYSLINUX_ENTRIES, UNIT)
    )
    assert len(entries) == 3
    assert entries[1].startswith("LABEL osiris-installer\n")
    assert "MENU LABEL Osiris installer only (%ARCH%, BIOS)" in entries[1]


def test_syslinuxs_installer_entry_boots_the_installer_target() -> None:
    entries = syslinux_entries(
        syslinux_with_installer_entry(RELENG_SYSLINUX_ENTRIES, UNIT)
    )
    assert entries[1].endswith(f"%KERNEL_PARAMS% systemd.unit={UNIT}")


def test_syslinuxs_installer_entry_explains_itself() -> None:
    entries = syslinux_entries(
        syslinux_with_installer_entry(RELENG_SYSLINUX_ENTRIES, UNIT)
    )
    assert "live medium" not in entries[1]


def test_syslinuxs_live_entry_is_unchanged() -> None:
    entries = syslinux_entries(
        syslinux_with_installer_entry(RELENG_SYSLINUX_ENTRIES, UNIT)
    )
    assert entries[0] == syslinux_entries(RELENG_SYSLINUX_ENTRIES)[0]


def test_a_syslinux_menu_without_releng_entry_is_refused() -> None:
    with pytest.raises(ValueError):
        syslinux_with_installer_entry("DEFAULT arch\n", UNIT)
