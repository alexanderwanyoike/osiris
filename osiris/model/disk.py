"""Disks the installer can offer, and whether each one is fit to install onto.

Pure description: nothing here opens a device or runs a command.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# Enough room for the base system, a desktop and somewhere to put files. Below
# this the install succeeds and the machine is unusable, which is worse than
# refusing.
MINIMUM_BYTES = 16 * 1000**3


class Filesystem(StrEnum):
    EXT4 = "ext4"
    BTRFS = "btrfs"


@dataclass(frozen=True)
class Disk:
    """A block device that might be installed onto."""

    path: str
    size: int
    label: str = "Disk"
    transport: str = ""
    mounted: bool = False

    @property
    def too_small(self) -> bool:
        return self.size < MINIMUM_BYTES

    @property
    def usable(self) -> bool:
        """Mounted disks are refused.

        A mounted disk is almost always the medium being booted from. Erasing
        it fails halfway through with an I/O error that says nothing useful.
        """
        return not (self.too_small or self.mounted)

    @property
    def unusable_because(self) -> str | None:
        if self.too_small:
            return f"too small - needs {human(MINIMUM_BYTES)}"
        if self.mounted:
            return "in use - cannot be erased while mounted"
        return None


def human(size: int) -> str:
    """Disk sizes, in the units the manufacturer printed on the box."""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1000:
            precision = 0 if unit in ("B", "KB") else 1
            return f"{value:.{precision}f} {unit}"
        value /= 1000
    return f"{value:.1f} TB"
