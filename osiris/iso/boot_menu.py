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


#: What releng calls Arch Linux in its menus, and what Osiris calls it instead.
#: Phrases rather than every "Arch Linux": the medium is Arch underneath, and a
#: blanket replace would also rewrite the mentions that are still true.
RENAMES = (
    ("Arch Linux install medium", "Osiris install medium"),
    ("MENU TITLE Arch Linux", "MENU TITLE Osiris"),
    ("install Arch Linux", "install Osiris"),
)


def rebranded(text: str) -> str:
    """`text` with the menus naming Osiris rather than Arch Linux."""
    for arch, osiris in RENAMES:
        text = text.replace(arch, osiris)
    return text


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


#: syslinux modules that work only through APM, which most firmware has dropped.
#: On a machine without it the entry does nothing at all.
APM_MODULES = ("reboot.c32", "poweroff.c32")


def without_apm_entries(text: str) -> str:
    """A syslinux menu without the entries that only work through APM.

    releng separates its entries with blank lines, so an entry is a paragraph.
    """
    paragraphs = text.rstrip("\n").split("\n\n")
    kept = [
        paragraph
        for paragraph in paragraphs
        if not any(f"COM32 {module}" in paragraph for module in APM_MODULES)
    ]
    return "\n\n".join(kept) + "\n"
