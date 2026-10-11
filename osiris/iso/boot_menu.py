"""The install medium's boot menus: archiso's releng configuration, rebranded.

releng's menus are kept as upstream writes them, so every entry and fix Arch
makes keeps arriving; these functions change only what Osiris has to.
"""

from __future__ import annotations

from collections.abc import Sequence

#: The directories of releng's profile that hold boot menu configuration.
CONFIG_DIRS = ("efiboot", "syslinux", "grub")

#: Suffixes of the files in those directories that are configuration.
CONFIG_SUFFIXES = (".conf", ".cfg")


def rebranded(text: str) -> str:
    """`text` with the menu entries called Osiris rather than Arch Linux."""
    return text.replace("Arch Linux install medium", "Osiris install medium")


#: The line in releng's graphics block that keeps the menu on the text console.
CONSOLE_OUTPUT = "    terminal_output console\nfi\n"


def themed(text: str, theme_dir: str, fonts: Sequence[str]) -> str:
    """releng's grub.cfg drawing its menu with the theme in `theme_dir`.

    archiso's embedded GRUB sets `root` to the medium before reading this
    file, so `theme_dir` is a path on the medium. A theme only finds fonts
    that are already loaded, which is why each one is loaded first.
    """
    if CONSOLE_OUTPUT not in text:
        raise ValueError("releng's grub.cfg no longer has the expected graphics block")
    lines = [
        "    terminal_output gfxterm",
        "    insmod png",
        *(f"    loadfont {theme_dir}/{font}" for font in fonts),
        f"    set theme={theme_dir}/theme.txt",
        "    export theme",
    ]
    return text.replace(CONSOLE_OUTPUT, "\n".join(lines) + "\nfi\n", 1)
