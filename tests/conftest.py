"""Fixtures shared across test modules."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import parted
import pytest
from archinstall.lib.disk.device_handler import device_handler
from archinstall.lib.locale import utils as locale_utils
from archinstall.lib.models.device import BDevice, _DeviceInfo

GIB = 1024**3

#: Console keymaps, as `localectl list-keymaps` prints them on Arch.
KEYMAPS = ["de", "fr", "uk", "us"]


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
