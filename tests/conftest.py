"""Fixtures shared across test modules."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import parted
import pytest
from archinstall.lib.disk.device_handler import device_handler
from archinstall.lib.models.device import BDevice, _DeviceInfo

GIB = 1024**3


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
