"""Services every Osiris install needs, regardless of desktop.

Exists because the desktop and application configurators each used to enable their
own list, and the Cinnamon one silently omitted NetworkManager and sshd - which
produced an installed system with no network and no way in. One list, imported
by both.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import run  # noqa: E402

COMMON = [
    "NetworkManager",     # without this an installed system has no network
    "sshd",
    "systemd-timesyncd",
]


def enable(*extra: str) -> None:
    """Enable the common services plus any desktop-specific ones."""
    for unit in (*COMMON, *extra):
        run("systemctl", "enable", unit)
