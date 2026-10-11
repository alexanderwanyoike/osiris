"""The install medium's boot menus, rebranded from archiso's releng profile."""

from __future__ import annotations

from osiris.iso.boot_menu import rebranded

SYSLINUX_ENTRY = "MENU LABEL Arch Linux install medium (%ARCH%, BIOS)\n"


def test_entries_are_called_osiris() -> None:
    assert rebranded(SYSLINUX_ENTRY) == (
        "MENU LABEL Osiris install medium (%ARCH%, BIOS)\n"
    )


def test_text_without_an_entry_name_is_unchanged() -> None:
    assert rebranded("timeout 15\n") == "timeout 15\n"
