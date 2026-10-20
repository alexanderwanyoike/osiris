"""Fixtures shared across test modules."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import parted
import pytest
from archinstall.lib.disk.device_handler import device_handler
from archinstall.lib.locale import utils as locale_utils
from archinstall.lib.models.device import (
    BDevice,
    FilesystemType,
    LsblkInfo,
    _DeviceInfo,
    _PartitionInfo,
)

from osiris.platform import FakeRunner
from osiris.platform.process import Result

GIB = 1024**3

#: Console keymaps, as `localectl list-keymaps` prints them on Arch.
KEYMAPS = ["de", "fr", "uk", "us"]


def an_archinstall_that_completes() -> FakeRunner:
    """A runner whose archinstall exits as a finished install does."""
    output = "Installation completed without any errors.\nYou may reboot when ready.\n"
    return FakeRunner(results={"archinstall": Result(("archinstall",), 0, output)})


@pytest.fixture(autouse=True)
def keymaps(monkeypatch: pytest.MonkeyPatch) -> None:
    """The keymaps archinstall validates a configuration against.

    archinstall asks `localectl list-keymaps`, which reads the console keymaps
    the kbd package installs. CI runs on Ubuntu, which has none, so every
    configuration read back there failed validation. A fixed list keeps the
    tests about the configuration rather than about the machine running them.
    """
    monkeypatch.setattr(locale_utils, "list_keyboard_languages", lambda: KEYMAPS)


@pytest.fixture
def device(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[BDevice]:
    """A 40 GiB disk, as archinstall sees one, backed by a sparse file.

    archinstall's parser looks devices up through its device handler, which
    only knows real hardware, so that one lookup is pointed at the image.
    """
    image = tmp_path / "disk.img"
    with image.open("wb") as handle:
        handle.truncate(40 * GIB)
    disk = parted.freshDisk(parted.getDevice(str(image)), "gpt")
    bdevice = BDevice(disk, _DeviceInfo.from_disk(disk), [])
    monkeypatch.setattr(device_handler, "get_device", lambda _path: bdevice)
    yield bdevice


def _lsblk(partition: parted.Partition, fstype: str) -> LsblkInfo:
    """What lsblk would report for a partition of the image."""
    return LsblkInfo.model_validate(
        {
            "name": partition.path.rsplit("/", 1)[-1],
            "path": partition.path,
            "pkname": None,
            "log-sec": 512,
            "size": int(partition.getLength(unit="B")),
            "pttype": "gpt",
            "ptuuid": None,
            "rota": False,
            "tran": None,
            "partn": partition.number,
            "partuuid": None,
            "parttype": None,
            "uuid": None,
            "fstype": fstype,
            "fsver": None,
            "fsavail": None,
            "fsuse%": None,
            "type": "part",
            "mountpoint": None,
            "mountpoints": [],
            "fsroots": [],
        }
    )


def a_disk_with(
    tmp_path: Path, partitions: list[tuple[int, int, FilesystemType, bool]]
) -> BDevice:
    """A 40 GiB GPT image holding `partitions`: (start MiB, size MiB, fs, esp)."""
    image = tmp_path / "shared.img"
    with image.open("wb") as handle:
        handle.truncate(40 * GIB)
    device = parted.getDevice(str(image))
    disk = parted.freshDisk(device, "gpt")
    mib = 1024**2 // device.sectorSize
    infos = []
    for start, size, _fs_type, esp in partitions:
        geometry = parted.Geometry(device, start=start * mib, length=size * mib)
        partition = parted.Partition(
            disk=disk, type=parted.PARTITION_NORMAL, geometry=geometry
        )
        disk.addPartition(partition, constraint=device.optimalAlignedConstraint)
        if esp:
            partition.setFlag(parted.PARTITION_ESP)
    for partition, (_, _, fs_type, _) in zip(disk.partitions, partitions, strict=True):
        infos.append(
            _PartitionInfo.from_partition(
                partition, _lsblk(partition, fs_type.value), fs_type
            )
        )
    return BDevice(disk, _DeviceInfo.from_disk(disk), infos)


@pytest.fixture
def shared_device(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BDevice:
    """Another system already installed: a 512 MiB ESP, a 20 GiB ext4 root,
    and about 19.5 GiB unallocated after them."""
    bdevice = a_disk_with(
        tmp_path,
        [
            (1, 512, FilesystemType.FAT32, True),
            (513, 20480, FilesystemType.EXT4, False),
        ],
    )
    monkeypatch.setattr(device_handler, "get_device", lambda _path: bdevice)
    return bdevice
