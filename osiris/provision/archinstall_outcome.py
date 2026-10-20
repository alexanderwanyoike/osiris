"""Whether archinstall installed anything, judged from what it printed.

Its exit code is not enough. archinstall 4.5 returns 0 having installed
nothing when it finds itself offline, and when it rejects the bootloader
layout in silent mode, so the exit code and the output have to agree.
"""

from __future__ import annotations

#: Printed by archinstall's Installer when its context closes cleanly: after
#: the custom commands, osiris-setup among them, have run without raising and
#: every step it tracks (base system, bootloader, ...) reported done.
#: osiris-setup's own OSIRIS_SETUP_DONE never reaches this output, because
#: archinstall captures custom commands' output without printing it.
COMPLETED = "Installation completed without any errors"


def failure(returncode: int, output: str) -> str | None:
    """Why the install did not happen, or None when it did."""
    if returncode == 0 and COMPLETED in output:
        return None
    if returncode == 0:
        return "archinstall stopped without installing anything."
    return f"archinstall exited {returncode} before the install finished."
