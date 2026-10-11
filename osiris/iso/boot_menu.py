"""The install medium's boot menus: archiso's releng configuration, rebranded.

releng's menus are kept as upstream writes them, so every entry and fix Arch
makes keeps arriving; these functions change only what Osiris has to.
"""

from __future__ import annotations

#: The directories of releng's profile that hold boot menu configuration.
CONFIG_DIRS = ("efiboot", "syslinux", "grub")

#: Suffixes of the files in those directories that are configuration.
CONFIG_SUFFIXES = (".conf", ".cfg")


def rebranded(text: str) -> str:
    """`text` with the menu entries called Osiris rather than Arch Linux."""
    return text.replace("Arch Linux install medium", "Osiris install medium")
