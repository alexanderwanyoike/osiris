"""Osiris's settings in /etc/default/grub, merged into what is already there.

The file is not Osiris's to overwrite. archinstall writes the kernel command
line into GRUB_CMDLINE_LINUX - the root device, the subvolume, and on an
encrypted install the parameters without which the disk cannot be unlocked.
Replacing the file wholesale would boot to a rescue shell, or not at all. So
only the keys below are set, each in place where it already appears, and
everything else is kept as written.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

THEME = "/boot/grub/themes/osiris/theme.txt"

SETTINGS: Mapping[str, str] = {
    "GRUB_TIMEOUT": "3",
    "GRUB_TIMEOUT_STYLE": "menu",
    "GRUB_DISTRIBUTOR": '"Osiris"',
    # Kept quiet so Plymouth has the screen. archinstall adds `quiet splash`
    # to GRUB_CMDLINE_LINUX; this is the rest.
    "GRUB_CMDLINE_LINUX_DEFAULT": (
        '"loglevel=3 rd.udev.log_level=3 vt.global_cursor_default=0"'
    ),
    # The theme needs a graphical mode. `auto` takes the firmware's preferred
    # resolution; `keep` holds it through the handover, so Plymouth does not
    # bring the mode up again and flicker.
    "GRUB_GFXMODE": "auto",
    "GRUB_GFXPAYLOAD_LINUX": "keep",
    "GRUB_THEME": f'"{THEME}"',
    "GRUB_DISABLE_RECOVERY": "true",
    # Arch ships this off. Finding the other systems on a dual-boot machine is
    # the main practical reason Osiris boots with GRUB.
    "GRUB_DISABLE_OS_PROBER": "false",
}


def merged(text: str, settings: Mapping[str, str] = SETTINGS) -> str:
    """`text` with each setting applied.

    A key that is present - commented out or not - is replaced on its first
    line; one that is absent is appended. No other line changes.
    """
    lines = text.splitlines()
    missing = dict(settings)
    for index, line in enumerate(lines):
        match = re.match(r"^\s*#?\s*([A-Z_]+)=", line)
        if match is None or match.group(1) not in missing:
            continue
        key = match.group(1)
        lines[index] = f"{key}={missing.pop(key)}"
    if missing:
        lines += ["", "# Osiris"]
        lines += [f"{key}={value}" for key, value in missing.items()]
    return "\n".join(lines) + "\n"
