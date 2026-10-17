"""Where on the disk Osiris goes.

Three modes, and the difference between them is what gets destroyed:

* **Whole disk** - the partition table is replaced. Everything goes.
* **Free space** - Osiris is written into unallocated space. Nothing that
  exists is touched.
* **Existing partition** - one chosen partition becomes the root and is
  formatted. Everything else is left alone.

Deliberately absent: shrinking an existing partition to make room, which is
what Mint's "install alongside" does. An online resize of a filesystem holding
someone's data is the single operation in an installer most likely to lose it,
and "make space first, then install into it" costs the user one step and
removes the whole class of failure. The installer opens GParted for that step.

Installing alongside another system needs UEFI and a GPT disk: Osiris shares
the existing EFI system partition rather than touching the other system's boot
code, and a BIOS machine has none to share.

Encryption needs the kernels outside the encrypted root. They are when Osiris
has its own boot partition - erasing the disk, or free space on a disk with no
EFI system partition yet - and are not when an existing one is shared, because
a shared ESP holds only GRUB and the kernels stay in /boot on the root. GRUB
would then have to unlock the root itself, which archinstall does not set up.
So that combination is refused here rather than installed and left unbootable.

Everything here is a description. Nothing opens a device.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from osiris.model.disk import MINIMUM_BYTES, Disk, Filesystem, human

#: An ESP shared with another operating system is usually this small, and
#: GRUB needs little. Refusing to install into a cramped one is better than
#: filling it and breaking the other system's bootloader.
MINIMUM_ESP_BYTES = 128 * 1000**2


class InstallMode(StrEnum):
    WHOLE_DISK = "whole-disk"
    FREE_SPACE = "free-space"
    EXISTING_PARTITION = "existing-partition"


@dataclass(frozen=True)
class Partition:
    """One partition that already exists on a disk."""

    path: str
    number: int
    size: int
    filesystem: str = ""
    label: str = ""
    mounted: bool = False
    esp: bool = False

    @property
    def description(self) -> str:
        parts = [self.path, human(self.size)]
        if self.filesystem:
            parts.append(self.filesystem)
        if self.label:
            parts.append(f'"{self.label}"')
        return "  ".join(parts)


@dataclass(frozen=True)
class FreeRegion:
    """Unallocated space on a disk."""

    start: int
    size: int

    @property
    def big_enough(self) -> bool:
        return self.size >= MINIMUM_BYTES


@dataclass(frozen=True)
class DiskContents:
    """What is already on a disk, as read from its partition table."""

    disk: Disk
    partitions: tuple[Partition, ...] = field(default_factory=tuple)
    free: tuple[FreeRegion, ...] = field(default_factory=tuple)
    gpt: bool = True

    @property
    def existing_esp(self) -> Partition | None:
        """An EFI system partition already on the disk, if it is usable.

        Reused rather than recreated. It may hold another operating system's
        bootloader, and formatting it is how an install that promised to leave
        Windows alone stops Windows booting.
        """
        for partition in self.partitions:
            if partition.esp and partition.size >= MINIMUM_ESP_BYTES:
                return partition
        return None

    @property
    def largest_free(self) -> FreeRegion | None:
        usable = [region for region in self.free if region.big_enough]
        return max(usable, key=lambda region: region.size) if usable else None

    def modes(self, uefi: bool = True) -> list[InstallMode]:
        """Which modes this disk can actually offer on this machine."""
        available = [InstallMode.WHOLE_DISK]
        if not (uefi and self.gpt):
            return available
        if self.largest_free is not None:
            available.append(InstallMode.FREE_SPACE)
        if any(self._can_be_root(p) for p in self.partitions):
            available.append(InstallMode.EXISTING_PARTITION)
        return available

    @staticmethod
    def _can_be_root(partition: Partition) -> bool:
        return (
            not partition.esp
            and not partition.mounted
            and partition.size >= MINIMUM_BYTES
        )

    def candidates_for_root(self) -> list[Partition]:
        return [p for p in self.partitions if self._can_be_root(p)]


@dataclass(frozen=True)
class Layout:
    """A decision about where Osiris goes, and what that costs."""

    contents: DiskContents
    mode: InstallMode = InstallMode.WHOLE_DISK
    filesystem: Filesystem = Filesystem.EXT4
    #: Which existing partition becomes the root, for EXISTING_PARTITION.
    root_partition: Partition | None = None
    #: The root is encrypted with LUKS.
    encrypted: bool = False

    @property
    def disk(self) -> Disk:
        return self.contents.disk

    @property
    def formats_whole_disk(self) -> bool:
        return self.mode is InstallMode.WHOLE_DISK

    @property
    def reuses_esp(self) -> bool:
        return (
            self.mode is not InstallMode.WHOLE_DISK
            and self.contents.existing_esp is not None
        )

    @property
    def destroys(self) -> list[str]:
        """Exactly what this layout will erase, in words.

        The installer shows this before it does anything. An installer that
        says "everything on the disk you pick will be erased" when it means
        "one partition" trains people to ignore the warning.
        """
        if self.mode is InstallMode.WHOLE_DISK:
            if not self.contents.partitions:
                return [f"{self.disk.path} (currently empty)"]
            return [
                f"{partition.description}" for partition in self.contents.partitions
            ]
        if self.mode is InstallMode.EXISTING_PARTITION and self.root_partition:
            return [self.root_partition.description]
        return []

    @property
    def keeps(self) -> list[str]:
        """What survives. The other half of the sentence."""
        if self.mode is InstallMode.WHOLE_DISK:
            return []
        destroyed = set(self.destroys)
        return [
            partition.description
            for partition in self.contents.partitions
            if partition.description not in destroyed
        ]

    def describe(self) -> list[str]:
        lines = []
        if self.mode is InstallMode.WHOLE_DISK:
            lines.append("1 GB     new boot partition")
            lines.append(f"rest     Osiris root ({self.filesystem.value})")
        elif self.mode is InstallMode.FREE_SPACE:
            region = self.contents.largest_free
            size = human(region.size) if region else "free space"
            if self.reuses_esp:
                esp = self.contents.existing_esp
                lines.append(f"reuse    existing {esp.path if esp else 'ESP'}")
            else:
                lines.append("1 GB     new boot partition")
            lines.append(f"{size}   Osiris root ({self.filesystem.value})")
        else:
            root = self.root_partition
            lines.append(
                f"format   {root.path if root else '?'} "
                f"as Osiris root ({self.filesystem.value})"
            )
            if self.reuses_esp:
                esp = self.contents.existing_esp
                lines.append(f"reuse    existing {esp.path if esp else 'ESP'}")
        if self.filesystem is Filesystem.BTRFS:
            lines.append("         subvolumes @, @home, @log, @pkg")
        if self.encrypted:
            lines.append("         root encrypted with LUKS2")
        return lines

    @property
    def problems(self) -> list[str]:
        """Why this layout cannot be installed, if it cannot."""
        problems: list[str] = []
        if self.mode is InstallMode.FREE_SPACE:
            if self.contents.largest_free is None:
                problems.append(
                    f"no unallocated space of at least {human(MINIMUM_BYTES)}"
                )
        elif self.mode is InstallMode.EXISTING_PARTITION:
            if self.root_partition is None:
                problems.append("no partition chosen to install into")
            elif self.root_partition.mounted:
                problems.append(f"{self.root_partition.path} is in use")
            elif self.root_partition.size < MINIMUM_BYTES:
                problems.append(
                    f"{self.root_partition.path} is smaller than {human(MINIMUM_BYTES)}"
                )
            if self.contents.existing_esp is None:
                # Making one would mean repartitioning, which is the thing
                # this mode exists to avoid.
                problems.append("no EFI system partition on this disk to boot from")
        if self.encrypted and self.reuses_esp:
            problems.append(
                "encryption needs a boot partition of Osiris's own, and this "
                "disk's existing EFI system partition would be shared instead"
            )
        return problems
