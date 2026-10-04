"""What is on a disk, read through archinstall.

archinstall has already read the partition table - its device handler holds
every partition with its filesystem, flags and mountpoints - and its manual
partitioning screen already works out where the free space is, aligned the
way it will later create partitions. Both are used as they are, so the
installer offers exactly the space archinstall will accept.
"""

from __future__ import annotations

from archinstall.lib.disk.device_handler import device_handler
from archinstall.lib.disk.partitioning_menu import FreeSpace, PartitioningList
from archinstall.lib.models.device import (
    BDevice,
    DeviceModification,
    PartitionFlag,
    PartitionModification,
    PartitionTable,
    Unit,
)

from osiris.model.disk import Disk
from osiris.model.layout import DiskContents, FreeRegion, Partition


def read(device: BDevice) -> DiskContents:
    """The partitions and free space on `device`."""
    using_gpt = device.disk.type == "gpt"
    info = device.device_info
    partitions = tuple(
        Partition(
            path=str(part.path),
            number=part.partn or 0,
            size=part.length.convert(Unit.B).value,
            filesystem=part.fs_type.value if part.fs_type else "",
            label=part.name or "",
            mounted=bool(part.mountpoints),
            esp=PartitionFlag.ESP in part.flags,
        )
        for part in device.partition_infos
    )
    return DiskContents(
        disk=Disk(
            path=str(info.path),
            size=info.total_size.convert(Unit.B).value,
            label=info.model,
            mounted=any(partition.mounted for partition in partitions),
        ),
        partitions=partitions,
        free=_free_regions(device, using_gpt),
        gpt=using_gpt,
    )


def _free_regions(device: BDevice, using_gpt: bool) -> tuple[FreeRegion, ...]:
    """Unallocated space, as archinstall's own partitioning screen sees it."""
    table = PartitionTable.GPT if using_gpt else PartitionTable.MBR
    existing = [
        PartitionModification.from_existing_partition(part)
        for part in device.partition_infos
    ]
    screen = PartitioningList(DeviceModification(device, wipe=False), table)
    return tuple(
        FreeRegion(
            start=segment.start.convert(Unit.B).value,
            size=segment.length.convert(Unit.B).value,
        )
        for segment in (s.segment for s in screen.as_segments(existing))
        if isinstance(segment, FreeSpace)
    )


def rescan() -> None:
    """Read every disk again, after something outside the installer changed one.

    archinstall reads the disks once, when it is imported; GParted can change
    them while the installer is open.
    """
    device_handler.load_devices()
