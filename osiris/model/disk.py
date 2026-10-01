"""Disks, and what an install will do to one.

Pure description. Nothing here opens a device or runs a command - it says what
the layout *will be*, so the installer can show it to the user before anything
is destroyed, and so the arithmetic can be tested without a disk.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# Enough room for the base system, a desktop and somewhere to put files. The
# ESP alone takes 1GB; below this the install succeeds and the machine is
# unusable, which is worse than refusing.
MINIMUM_BYTES = 16 * 1000**3
ESP_MEGABYTES = 1024


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

    def partition(self, number: int) -> str:
        """The device node for one of this disk's partitions.

        /dev/sda -> /dev/sda1, but /dev/nvme0n1 -> /dev/nvme0n1p1. The rule is
        that a name ending in a digit takes a `p` separator, or the partition
        number would run into the device number.
        """
        separator = "p" if self.path[-1].isdigit() else ""
        return f"{self.path}{separator}{number}"

    @property
    def esp(self) -> str:
        return self.partition(1)

    @property
    def root(self) -> str:
        return self.partition(2)


def human(size: int) -> str:
    """Disk sizes, in the units the manufacturer printed on the box."""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1000:
            precision = 0 if unit in ("B", "KB") else 1
            return f"{value:.{precision}f} {unit}"
        value /= 1000
    return f"{value:.1f} TB"


@dataclass(frozen=True)
class Subvolume:
    name: str
    mountpoint: str | None
    options: str


@dataclass(frozen=True)
class PartitionPlan:
    """What the disk will look like afterwards, said before it happens."""

    disk: Disk
    filesystem: Filesystem
    swap_megabytes: int = 0

    @property
    def swap_file(self) -> str | None:
        """Where the swap file goes, relative to the installed root.

        On btrfs it lives on its own subvolume: a subvolume holding an active
        swap file cannot be snapshotted, and keeping it off `@` keeps that
        limitation off the root.
        """
        if not self.swap_megabytes:
            return None
        return "/swap/swapfile" if self.filesystem is Filesystem.BTRFS else "/swapfile"

    @property
    def subvolumes(self) -> tuple[Subvolume, ...]:
        if self.filesystem is not Filesystem.BTRFS:
            return ()
        volumes = [
            Subvolume("@", "/mnt", BTRFS_OPTIONS),
            Subvolume("@home", "/mnt/home", BTRFS_OPTIONS),
        ]
        if self.swap_megabytes:
            # No compression on the swap subvolume: a compressed or
            # copy-on-write file cannot be swapped on at all.
            volumes.append(Subvolume("@swap", "/mnt/swap", "noatime"))
        return tuple(volumes)

    @property
    def root_flags(self) -> str:
        """Kernel parameters the root filesystem needs to be mountable.

        Without this btrfs mounts the top-level volume and finds no init.
        """
        return "rootflags=subvol=@" if self.filesystem is Filesystem.BTRFS else ""

    def describe(self) -> list[str]:
        """The plan in words, for the installer to show before committing."""
        lines = [
            f"{ESP_MEGABYTES} MB  EFI system partition (FAT32)",
            f"rest     Osiris root ({self.filesystem.value})",
        ]
        if self.subvolumes:
            names = ", ".join(volume.name for volume in self.subvolumes)
            lines.append(f"         subvolumes {names}")
        if self.swap_megabytes:
            lines.append(f"{self.swap_megabytes} MB  swap file")
        return lines


# zstd:1 is the cheap end of the scale: it saves space on a package-heavy root
# without the write latency of the higher levels.
BTRFS_OPTIONS = "compress=zstd:1,noatime,ssd"
