"""Installing beside another system: what is touched, and what is not.

The disk holds another system - an EFI system partition and an ext4 root -
with free space after it. Every layout is read back through archinstall's
parser, the path `archinstall --config` takes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from archinstall.lib.args import ArchConfig, Arguments
from archinstall.lib.disk.device_handler import device_handler
from archinstall.lib.models.device import (
    BDevice,
    FilesystemType,
    ModificationStatus,
    PartitionFlag,
    PartitionModification,
    Unit,
)

from osiris.model.disk import Disk, Filesystem
from osiris.model.hardware import Hardware
from osiris.model.layout import InstallMode, Layout
from osiris.model.request import InstallRequest, InvalidRequest
from osiris.platform import FakeRunner
from osiris.platform.hardware import FakeProbe
from osiris.provision import archinstall_config as config
from osiris.provision import disk_contents
from osiris.provision.installer import Installer
from tests.conftest import GIB, a_disk_with, an_archinstall_that_completes

MIB = 1024**2


def a_request(device: BDevice, **overrides: Any) -> InstallRequest:
    defaults: dict[str, Any] = {
        "disk": Disk(str(device.device_info.path), 40 * GIB),
        "username": "alex",
        "password": "osiris123",
    }
    return InstallRequest(**{**defaults, **overrides})


def installed(
    device: BDevice, tmp_path: Path, uefi: bool = True, **overrides: Any
) -> ArchConfig:
    """Run the installer against the image and parse what it wrote."""
    Installer(
        an_archinstall_that_completes(),
        FakeProbe(Hardware()),
        devices=lambda _path: device,
        using_gpt=True,
        uefi=uefi,
        config_dir=tmp_path / "out",
    ).install(a_request(device, **overrides))
    written = json.loads((tmp_path / "out" / "config.json").read_text())
    return ArchConfig.from_config(written, Arguments())


def by_path(parsed: ArchConfig) -> dict[str, PartitionModification]:
    assert parsed.disk_config is not None
    (modification,) = parsed.disk_config.device_modifications
    assert not modification.wipe, "the partition table is kept"
    return {str(p.dev_path): p for p in modification.partitions if p.dev_path}


def created(parsed: ArchConfig) -> list[PartitionModification]:
    assert parsed.disk_config is not None
    (modification,) = parsed.disk_config.device_modifications
    return [p for p in modification.partitions if p.status is ModificationStatus.CREATE]


class TestReadingTheDisk:
    def test_the_other_system_and_the_free_space_are_seen(
        self, shared_device: BDevice
    ) -> None:
        contents = disk_contents.read(shared_device)
        esp, other = contents.partitions
        assert esp.esp and esp.filesystem == "fat32"
        assert other.filesystem == "ext4" and not other.esp
        assert contents.existing_esp == esp
        region = contents.largest_free
        assert region is not None
        assert region.start == 20993 * MIB
        assert 19 * GIB < region.size < 20 * GIB


class TestFreeSpace:
    def test_the_other_system_is_left_exactly_as_it_was(
        self, shared_device: BDevice, tmp_path: Path
    ) -> None:
        parts = by_path(installed(shared_device, tmp_path, mode=InstallMode.FREE_SPACE))
        _esp, other = (str(p.path) for p in shared_device.partition_infos)
        assert parts[other].status is ModificationStatus.EXIST
        assert parts[other].mountpoint is None

    def test_the_esp_is_shared_not_formatted(
        self, shared_device: BDevice, tmp_path: Path
    ) -> None:
        parts = by_path(installed(shared_device, tmp_path, mode=InstallMode.FREE_SPACE))
        esp = parts[str(shared_device.partition_infos[0].path)]
        assert esp.status is ModificationStatus.EXIST
        assert esp.mountpoint == config.SHARED_ESP
        assert PartitionFlag.ESP in esp.flags

    def test_the_root_fills_the_free_space(
        self, shared_device: BDevice, tmp_path: Path
    ) -> None:
        (root,) = created(
            installed(shared_device, tmp_path, mode=InstallMode.FREE_SPACE)
        )
        other = shared_device.partition_infos[1]
        assert (
            root.start.convert(Unit.B).value
            == (other.start + other.length).convert(Unit.B).value
        )
        assert root.fs_type is FilesystemType.EXT4
        assert root.mountpoint == Path("/")

    def test_btrfs_gets_the_same_subvolumes_as_a_whole_disk(
        self, shared_device: BDevice, tmp_path: Path
    ) -> None:
        (root,) = created(
            installed(
                shared_device, tmp_path,
                mode=InstallMode.FREE_SPACE, filesystem=Filesystem.BTRFS,
            )
        )  # fmt: skip
        assert [str(v.name) for v in root.btrfs_subvols][:2] == ["@", "@home"]

    def test_the_removable_fallback_is_not_overwritten(
        self, shared_device: BDevice, tmp_path: Path
    ) -> None:
        """On a shared ESP, /EFI/BOOT/BOOTX64.EFI belongs to the other system."""
        parsed = installed(shared_device, tmp_path, mode=InstallMode.FREE_SPACE)
        assert parsed.bootloader_config is not None
        assert not parsed.bootloader_config.removable

    def test_a_disk_without_an_esp_gets_a_new_one_in_the_free_space(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        device = a_disk_with(tmp_path, [(1, 10240, FilesystemType.EXT4, False)])
        monkeypatch.setattr(device_handler, "get_device", lambda _path: device)
        boot, root = created(installed(device, tmp_path, mode=InstallMode.FREE_SPACE))
        assert PartitionFlag.ESP in boot.flags
        assert boot.mountpoint == Path("/boot")
        assert boot.start.convert(Unit.B).value == 10241 * MIB
        assert root.start == boot.start + boot.length


class TestExistingPartition:
    def test_only_the_chosen_partition_is_formatted(
        self, shared_device: BDevice, tmp_path: Path
    ) -> None:
        esp_path, other_path = (str(p.path) for p in shared_device.partition_infos)
        parsed = installed(
            shared_device, tmp_path,
            mode=InstallMode.EXISTING_PARTITION, root_partition=other_path,
        )  # fmt: skip
        parts = by_path(parsed)
        assert parts[other_path].status is ModificationStatus.MODIFY
        assert parts[other_path].mountpoint == Path("/")
        assert parts[esp_path].status is ModificationStatus.EXIST
        assert created(parsed) == []

    def test_the_esp_cannot_be_chosen(
        self, shared_device: BDevice, tmp_path: Path
    ) -> None:
        esp_path = str(shared_device.partition_infos[0].path)
        with pytest.raises(InvalidRequest):
            installed(
                shared_device, tmp_path,
                mode=InstallMode.EXISTING_PARTITION, root_partition=esp_path,
            )  # fmt: skip


class TestRefusals:
    def test_a_bios_machine_cannot_install_alongside(
        self, shared_device: BDevice, tmp_path: Path
    ) -> None:
        with pytest.raises(InvalidRequest):
            installed(shared_device, tmp_path, uefi=False, mode=InstallMode.FREE_SPACE)

    def test_nothing_runs_when_the_layout_is_refused(
        self, shared_device: BDevice, tmp_path: Path
    ) -> None:
        runner = FakeRunner()
        installer = Installer(
            runner, FakeProbe(Hardware()), devices=lambda _path: shared_device,
            using_gpt=True, uefi=False, config_dir=tmp_path,
        )  # fmt: skip
        with pytest.raises(InvalidRequest):
            installer.install(a_request(shared_device, mode=InstallMode.FREE_SPACE))
        assert runner.calls == []

    def test_a_layout_with_no_free_space_is_not_built(
        self, shared_device: BDevice
    ) -> None:
        contents = disk_contents.read(shared_device)
        empty = Layout(
            type(contents)(contents.disk, contents.partitions, ()),
            InstallMode.FREE_SPACE,
        )
        with pytest.raises(ValueError):
            config.alongside_layout(shared_device, empty)
