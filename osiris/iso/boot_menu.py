"""The install medium's boot menus: archiso's releng configuration, rebranded.

releng's menus are kept as upstream writes them, so every entry and fix Arch
makes keeps arriving; these functions change only what Osiris has to.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

#: The directories of releng's profile that hold boot menu configuration.
CONFIG_DIRS = ("efiboot", "syslinux", "grub")

#: Suffixes of the files in those directories that are configuration.
CONFIG_SUFFIXES = (".conf", ".cfg")


#: What releng calls Arch Linux in its menus, and what Osiris calls it instead.
#: Phrases rather than every "Arch Linux": the medium is Arch underneath, and a
#: blanket replace would also rewrite the mentions that are still true.
LIVE_NAME = "Osiris live medium"

RENAMES = (
    ("Arch Linux install medium", LIVE_NAME),
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


#: The second entry: the installer on bare X, for a machine whose graphics will
#: not bring the live desktop up. It boots `unit` in place of the default target.
INSTALLER_NAME = "Osiris installer only"
INSTALLER_HELP = """TEXT HELP
Boot straight into the Osiris installer, without the live desktop.
For machines where the desktop does not start.
ENDTEXT"""

_GRUB_LIVE_ENTRY = re.compile(
    r"^menuentry \"[^\"]*\"[^\n]*--id 'archlinux' \{\n.*?^\}\n",
    re.MULTILINE | re.DOTALL,
)
_SYSLINUX_HELP = re.compile(r"^TEXT HELP\n.*?^ENDTEXT", re.MULTILINE | re.DOTALL)


def _booting(entry: str, unit: str) -> str:
    return entry.replace("%KERNEL_PARAMS%", f"%KERNEL_PARAMS% systemd.unit={unit}")


def grub_with_installer_entry(text: str, unit: str) -> str:
    """releng's grub.cfg with the installer-only entry after the live one."""
    live = _GRUB_LIVE_ENTRY.search(text)
    if live is None:
        raise ValueError("releng's grub.cfg no longer has its 'archlinux' entry")
    installer = _booting(
        live.group(0)
        .replace(LIVE_NAME, INSTALLER_NAME, 1)
        .replace("--id 'archlinux'", "--id 'osiris-installer'"),
        unit,
    )
    return text[: live.end()] + "\n" + installer + text[live.end() :]


def syslinux_with_installer_entry(text: str, unit: str) -> str:
    """releng's archiso_sys-linux.cfg with the installer-only entry second."""
    entries = text.rstrip("\n").split("\n\n")
    live = next((e for e in entries if e.startswith("LABEL arch\n")), None)
    if live is None:
        raise ValueError("releng's syslinux menu no longer has its 'arch' entry")
    installer = _booting(
        _SYSLINUX_HELP.sub(INSTALLER_HELP, live, count=1)
        .replace("LABEL arch\n", "LABEL osiris-installer\n", 1)
        .replace(LIVE_NAME, INSTALLER_NAME),
        unit,
    )
    entries.insert(entries.index(live) + 1, installer)
    return "\n\n".join(entries) + "\n"
